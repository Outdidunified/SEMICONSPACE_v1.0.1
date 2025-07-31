import { Injectable, Logger } from '@nestjs/common';
import { Cron } from '@nestjs/schedule';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { CartItem } from './cart-item.entity';
import { RedisService } from '../redis/redis.service';

@Injectable()
export class CartSyncService {
  private readonly logger = new Logger(CartSyncService.name);

  constructor(
    private readonly redisService: RedisService,
    @InjectRepository(CartItem)
    private readonly cartItemRepo: Repository<CartItem>,
  ) {}

  @Cron('*/10 * * * * *') // Runs every 10 seconds
  async syncCartToPostgres() {
    this.logger.log('🔄 Syncing cart data from Redis to PostgreSQL...');
    try {
      const redisClient = this.redisService.getClient();
      const keys = await redisClient.keys('cart:*');

      for (const key of keys) {
        const userId = key.split(':')[1];
        const cart = await redisClient.hGetAll(key);

        const entries = Object.entries(cart);
        console.log(`🔍 Redis Items for ${userId}:`, entries);

        const items: CartItem[] = entries
          .map(([productIdStr, jsonData]) => {
            try {
              const parsed = JSON.parse(jsonData);

              const productId = parseInt(productIdStr, 10);
              const quantity = parseInt(parsed.quantity, 10);

              if (isNaN(productId) || isNaN(quantity) || quantity <= 0) {
                return null;
              }

              return {
                userId,
                productId,
                quantity,
                externalProductId: parsed.externalProductId,
                supplier: parsed.supplier,
                name: parsed.name,
                price: parsed.price, // ✅ Ensure price is mapped here
                description: parsed.description,
                manufacturerId: parsed.manufacturerId,
                manufacturerPartNumber: parsed.manufacturerPartNumber,
                category: parsed.category,
                packageType: parsed.packageType,
                datasheetUrl: parsed.datasheetUrl,
                imageUrl: parsed.imageUrl,
                lastFetchedAt: parsed.lastFetchedAt ? new Date(parsed.lastFetchedAt) : undefined,
                categoryId: parsed.categoryId,
                createdBy: parsed.createdBy,
                modifiedBy: parsed.modifiedBy,
                createdDate: parsed.createdDate ? new Date(parsed.createdDate) : undefined,
                modifiedDate: parsed.modifiedDate ? new Date(parsed.modifiedDate) : undefined,
                status: parsed.status ?? true,
              } as CartItem;
            } catch (err) {
              this.logger.warn(`⚠️ Skipping invalid cart item for product ${productIdStr}: ${err.message}`);
              return null;
            }
          })
          .filter((item): item is CartItem => item !== null);

        // Remove existing entries for this user
        await this.cartItemRepo.delete({ userId });

        if (items.length > 0) {
          await this.cartItemRepo.save(items);
          this.logger.log(`✅ Synced ${items.length} items for user ${userId}`);
        } else {
          this.logger.warn(`⚠️ No valid items to sync for user ${userId}`);
        }
      }
    } catch (error) {
      this.logger.error('❌ Failed to sync cart:', error.message);
    }
  }
}
