import { Injectable, Logger } from "@nestjs/common";
import { Cron } from "@nestjs/schedule";
import { InjectRepository } from "@nestjs/typeorm";
import { Repository, DeepPartial } from "typeorm";
import { CartItem } from "./cart-item.entity";
import { RedisService } from "../redis/redis.service";

@Injectable()
export class CartSyncService {
  private readonly logger = new Logger(CartSyncService.name);

  constructor(
    private readonly redisService: RedisService,
    @InjectRepository(CartItem)
    private readonly cartItemRepo: Repository<CartItem>
  ) {}

  @Cron("*/10 * * * * *") // Runs every 10 seconds
  async syncCartToPostgres() {
    this.logger.log("🔄 Syncing cart data from Redis to PostgreSQL...");

    try {
      const redisClient = this.redisService.getClient();
      const keys = await redisClient.keys("cart:*");

      for (const key of keys) {
        const userId = key.split(":")[1];
        
        // Check if this user has recently completed payment (cart should not be synced)
        const paymentCompletedKey = `payment_completed:${userId}`;
        const paymentCompleted = await redisClient.get(paymentCompletedKey);
        
        if (paymentCompleted) {
          this.logger.log(`💳 Skipping sync for user ${userId} - payment recently completed`);
          
          // Clean up the payment completed flag and clear Redis cart
          await redisClient.del(paymentCompletedKey);
          await redisClient.del(key);
          
          // Ensure PostgreSQL is also cleared
          await this.cartItemRepo.delete({ userId });
          
          this.logger.log(`🧹 Cart cleared for user ${userId} after payment completion`);
          continue;
        }

        const cart = await redisClient.hGetAll(key);

        const entries = Object.entries(cart);
        this.logger.log(
          `🔍 Found ${entries.length} items in Redis for user ${userId}`
        );

        const items: DeepPartial<CartItem>[] = entries
          .map(([productIdStr, jsonData]) => {
            try {
              if (!jsonData) {
                this.logger.warn(
                  `⚠️ Empty value for product key ${productIdStr}`
                );
                return null;
              }

              const parsed = JSON.parse(jsonData as string);
              
              const productId = parsed.productId || parsed.semicon_part_number || parsed.id;
              const quantity = parseInt(parsed.quantity, 10);

              if (!productId || isNaN(quantity) || quantity <= 0) {
                this.logger.warn(
                  `⚠️ Skipping item: Invalid productId (${productId}) or quantity (${quantity})`
                );
                return null;
              }

              const item: DeepPartial<CartItem> = {
                userId,
                productId,
                quantity,
                name: parsed.name || '',
                price: parsed.price || 0,
                description: parsed.description || '',
                manufacturerName: parsed.manufacturerName || '',
                manufacturerPartNumber: parsed.manufacturerPartNumber || '',
                datasheetUrl: parsed.datasheetUrl || '',
                imageUrl: parsed.imageUrl || '',
                createdBy: userId,
                modifiedBy: userId,
                createdDate: parsed.createdDate ? new Date(parsed.createdDate) : new Date(),
                modifiedDate: new Date(),
                status: parsed.status ?? true,
              };

              return item;
            } catch (err) {
              this.logger.warn(
                `⚠️ Skipping invalid cart item: ${err.message}`
              );
              return null;
            }
          })
          .filter((item): item is DeepPartial<CartItem> => item !== null);

        // Clean existing cart items for this user
        await this.cartItemRepo.delete({ userId });

        if (items.length > 0) {
          await this.cartItemRepo.save(items);
          this.logger.log(`✅ Synced ${items.length} items for user ${userId}`);
        }
      }
    } catch (error) {
      this.logger.error("❌ Failed to sync cart:", error.message);
    }
  }
}
