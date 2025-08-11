// cart.service.ts
import { Injectable, Inject } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository, DeepPartial } from 'typeorm';
import { CartItem } from './cart-item.entity';
import { RedisService } from '../redis/redis.service';
import { ClientKafka } from '@nestjs/microservices';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';

@Injectable()
export class CartService {
  logger: any;
  constructor(
    @InjectRepository(CartItem)
    private readonly cartRepository: Repository<CartItem>,
    private readonly redisService: RedisService,
    private readonly httpService: HttpService,
    @Inject('KAFKA_SERVICE')
    private readonly kafkaClient: ClientKafka,
  ) {}
async handleAddToCart(body: { userId: string; productId: string; quantity: number }): Promise<any> {
  const { userId, productId, quantity } = body;
  const redis = this.redisService.getClient();
  const redisKey = `cart:${userId}`;
  const productIdKey = productId;

  if (quantity <= 0) {
    return this.handleRemoveFromCart(userId, productIdKey);
  }

  try {
    // 🧾 Log basic inputs
    console.log('🧾 Product ID:', productId);
    console.log('📦 Quantity:', quantity);

    // 📡 External API
    const externalUrl = `http://172.232.110.10:8003/product/quantity/check/${productId}/${quantity}`;
    console.log('➡️ Fetching product from:', externalUrl);

    const response = await firstValueFrom(this.httpService.get(externalUrl));
    const responseData = response.data;

    // 🧾 Log full response
    console.log('📦 Full external API response:', JSON.stringify(responseData, null, 2));

    const product = responseData?.data?.product;
    const price = product?.unit_price ?? 0;

    console.log('📦 Parsed product:', product);
    console.log('💲 Price:', price);

    // ❌ Validate response
    if (!product || product?.detail) {
      const message = product?.detail?.message || responseData?.message || 'Product not found';
      console.log('❌ Product fetch failed:', message);

      return {
        statusCode: 404,
        error: true,
        message,
      };
    }

    // 🛒 Build cart item
    const now = new Date();
    const cartItemData: DeepPartial<CartItem> = {
      userId,
      productId: product.semicon_part_number || productId, // fallback
      quantity,
      name: product.name || '',
      price,
      description: product.description || '',
      manufacturerName: product.manufacturer_name || '',
      manufacturerPartNumber: product.manufacturer_part_number || '',
      datasheetUrl: product.datasheet_url || '',
      imageUrl: product.image_url || '',
      createdBy: userId,
      modifiedBy: userId,
      createdDate: now,
      modifiedDate: now,
      status: product.status ?? true,
    };

    // ♻️ Redis
    await redis.hSet(redisKey, productIdKey, JSON.stringify(cartItemData));
    await redis.expire(redisKey, 86400); // 24h TTL

    // 🗃️ PostgreSQL: Upsert
    const existing = await this.cartRepository.findOne({ where: { userId, productId } });
    if (existing) {
      await this.cartRepository.update({ id: existing.id }, {
        ...cartItemData,
        quantity,
        modifiedDate: now,
      });
    } else {
      await this.cartRepository.save(cartItemData);
    }

    // 📣 Kafka event
    this.kafkaClient.emit('cart.item.added', {
      userId,
      productId,
      quantity,
      status: 'success',
      message: 'Cart item added or updated',
      timestamp: now.toISOString(),
    });

    // ✅ Return
    return {
      statusCode: 200,
      error: false,
      message: 'Item successfully added in cart',
      data: { userId, productId, quantity },
    };

  } catch (error) {
    console.error('❌ Error fetching product:', error?.message);
    console.error('❌ Full error response:', JSON.stringify(error?.response?.data, null, 2));

    const errMsg =
      error?.response?.data?.message ||
      error?.response?.data?.detail?.message ||
      error.message || 'Unknown error';

    return {
      statusCode: 500,
      error: true,
      message: errMsg,
    };
  }
}
async handleGetCartItems(userId: string): Promise<any> {
  const redis = this.redisService.getClient();
  const redisKey = `cart:${userId}`;

  try {
    let cart = await redis.hGetAll(redisKey);
    let entries = Object.entries(cart);

    // If Redis is empty, fetch from DB and rehydrate
    if (entries.length === 0) {
      const dbItems = await this.cartRepository.find({ where: { userId } });

      if (dbItems.length === 0) {
        return {
          statusCode: 404,
          error: true,
          message: `No items in cart for user ${userId}`,
        };
      }

      // Rehydrate Redis from DB
      const pipeline = redis.multi();
      for (const item of dbItems) {
        const itemProductId = item.productId?.toString?.() ?? '';
        pipeline.hSet(redisKey, itemProductId, JSON.stringify(item));
      }
      pipeline.expire(redisKey, 86400); // Set 24h TTL
      await pipeline.exec();

      cart = await redis.hGetAll(redisKey);
      entries = Object.entries(cart);
    }

    // Parse items from Redis
    const items = entries.map(([productIdKey, itemJson]) => {
      const item = JSON.parse(itemJson as string);
      const totalPrice = (item.price ?? 0) * (item.quantity ?? 0);
      return {
        ...item,
        productId: item.productId ?? productIdKey, // fallback to Redis key if missing
        totalPrice,
      };
    });

    const cartTotal = items.reduce((sum, item) => sum + item.totalPrice, 0);

    return {
      statusCode: 200,
      error: false,
      message: 'Cart items fetched successfully',
      data: {
        items,
        cartTotal,
      },
    };

  } catch (error) {
    console.error('❌ Error fetching cart items:', error);
    return {
      statusCode: 500,
      error: true,
      message: error.message || 'Failed to fetch cart items',
    };
  }
}

  async handleRemoveFromCart(userId: string, productId: string): Promise<any> {
    const redis = this.redisService.getClient();
    const redisKey = `cart:${userId}`;

    if (!userId || !productId) {
      return {
        statusCode: 400,
        error: true,
        message: 'Invalid userId or productId',
      };
    }

    try {
      // ✅ Step 1: Remove from Redis
      await redis.hDel(redisKey, productId);

      // ✅ Step 2: Remove from DB
      const existingItem = await this.cartRepository.findOne({
        where: { userId, productId }, // productId is now string
      });
      if (existingItem) {
        await this.cartRepository.remove(existingItem);
      }

      // ✅ Step 3: Emit Kafka
      this.kafkaClient.emit('cart.item.removed', {
        userId,
        productId,
        status: 'success',
        timestamp: new Date().toISOString(),
      });

      return {
        statusCode: 200,
        error: false,
        message: 'Item removed from cart',
        data: { userId, productId },
      };
    } catch (error) {
      this.kafkaClient.emit('cart.item.removed.error', {
        userId,
        productId,
        status: 'error',
        error: error.message,
        timestamp: new Date().toISOString(),
      });

      return {
        statusCode: 500,
        error: true,
        message: error.message || 'Failed to remove item from cart',
      };
    }
  }

  async clearCart(userId: string): Promise<any> {
    const redis = this.redisService.getClient();
    const redisKey = `cart:${userId}`;

    if (!userId) {
      return {
        statusCode: 400,
        error: true,
        message: 'Invalid userId',
      };
    }

    try {
      // ✅ Step 1: Remove from Redis
      await redis.del(redisKey);

      // ✅ Step 2: Remove all items from DB for this user
      const existingItems = await this.cartRepository.find({
        where: { userId },
      });
      
      if (existingItems.length > 0) {
        await this.cartRepository.remove(existingItems);
      }

      // ✅ Step 3: Emit Kafka
      this.kafkaClient.emit('cart.cleared', {
        userId,
        itemsCleared: existingItems.length,
        status: 'success',
        timestamp: new Date().toISOString(),
      });

      return {
        statusCode: 200,
        error: false,
        message: `Cart cleared successfully. ${existingItems.length} items removed.`,
        data: { userId, itemsCleared: existingItems.length },
      };
    } catch (error) {
      this.kafkaClient.emit('cart.cleared.error', {
        userId,
        status: 'error',
        error: error.message,
        timestamp: new Date().toISOString(),
      });

      return {
        statusCode: 500,
        error: true,
        message: error.message || 'Failed to clear cart',
      };
    }
  }
}






