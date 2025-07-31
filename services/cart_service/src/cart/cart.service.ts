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

  async handleAddToCart(body: { userId: string; productId: number; quantity: number }): Promise<any> {
    const { userId, productId, quantity } = body;
    const redis = this.redisService.getClient();
    const redisKey = `cart:${userId}`;
    const productIdKey = productId.toString();

    if (quantity <= 0) {
      return this.handleRemoveFromCart(userId, productIdKey);
    }

    try {
      const externalUrl = `http://172.232.110.10:8003/product/${productId}/${quantity}`;
      const response = await firstValueFrom(this.httpService.get(externalUrl));
      const product = response.data?.data?.product;
      const price = response.data?.data?.price;

      if (!product || product?.detail) {
        const message = product?.detail?.message || 'Product not found';
        return {
          statusCode: 404,
          error: true,
          message,
        };
      }

      const cartItemData: DeepPartial<CartItem> = {
        userId,
        productId,
        quantity,
        externalProductId: product.external_product_id,
        supplier: product.supplier,
        name: product.name,
        price,
        description: product.description,
        manufacturerId: product.manufacturer_id,
        manufacturerPartNumber: product.manufacturer_part_number,
        category: product.category,
        packageType: product.package_type,
        datasheetUrl: product.datasheet_url,
        imageUrl: product.image_url,
        lastFetchedAt: product.last_fetched_at ? new Date(product.last_fetched_at) : undefined,
        categoryId: product.category_id,
        createdBy: product.created_by,
        modifiedBy: product.modified_by,
        createdDate: product.created_date ? new Date(product.created_date) : undefined,
        modifiedDate: new Date(),
        status: product.status,
      };

      // ✅ Redis - update item
      await redis.hSet(redisKey, productIdKey, JSON.stringify(cartItemData));
      await redis.expire(redisKey, 86400); // Optional TTL: 24h

      // ✅ PostgreSQL - check if item exists, then update or insert
      const existing = await this.cartRepository.findOne({ where: { userId, productId } });
      if (existing) {
        await this.cartRepository.update({ id: existing.id }, {
          ...cartItemData,
          quantity,
          modifiedDate: new Date(),
        });
      } else {
        await this.cartRepository.save(cartItemData);
      }

      // ✅ Kafka emit
      this.kafkaClient.emit('cart.item.added', {
        userId,
        productId,
        quantity,
        status: 'success',
        message: 'Cart item added or updated',
        timestamp: new Date().toISOString(),
      });

      return {
        statusCode: 200,
        error: false,
        message: 'Item successfully added/updated in cart',
        data: { userId, productId, quantity },
      };

    } catch (error) {
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

      if (entries.length === 0) {
        const dbItems = await this.cartRepository.find({ where: { userId } });

        if (dbItems.length === 0) {
          return {
            statusCode: 404,
            error: true,
            message: `No items in cart for user ${userId}`,
          };
        }

        // ♻️ Rehydrate Redis
        const pipeline = redis.multi();
        for (const item of dbItems) {
          pipeline.hSet(redisKey, item.productId.toString(), JSON.stringify(item));
        }
        pipeline.expire(redisKey, 86400);
        await pipeline.exec();

        cart = await redis.hGetAll(redisKey);
        entries = Object.entries(cart);
      }

      const items = entries.map(([productId, itemJson]) => {
        const item = JSON.parse(itemJson);
        const totalPrice = (item.price ?? 0) * (item.quantity ?? 0);
        return { ...item, productId: parseInt(productId), totalPrice };
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
      return {
        statusCode: 500,
        error: true,
        message: error.message || 'Failed to fetch cart items',
      };
    }
  }

async handleRemoveFromCart(userId: string, productIdParam: string): Promise<any> {
  const redis = this.redisService.getClient();
  const redisKey = `cart:${userId}`;
  const productId = parseInt(productIdParam, 10);

  if (!userId || isNaN(productId)) {
    return {
      statusCode: 400,
      error: true,
      message: 'Invalid userId or productId',
    };
  }

  try {
    // ✅ Step 1: Remove from Redis (even if it doesn't exist)
    await redis.hDel(redisKey, productId.toString());

    // ✅ Step 2: Remove from DB
    const existingItem = await this.cartRepository.findOne({ where: { userId, productId } });
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




}
