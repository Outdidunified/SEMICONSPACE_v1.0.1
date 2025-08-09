import { Injectable, OnModuleInit, Logger } from '@nestjs/common';
import { Kafka } from 'kafkajs';
import { SearchService } from '../modules/search/search.service';

@Injectable()
export class KafkaConsumerService implements OnModuleInit {
  private readonly logger = new Logger(KafkaConsumerService.name);

  constructor(private readonly searchService: SearchService) {}

  async onModuleInit() {
    this.logger.log('⏳ Kafka Consumer initializing...');

    const kafka = new Kafka({
      clientId: 'search-service',
      brokers: [process.env.KAFKA_BROKER], 
    });

    const consumer = kafka.consumer({ groupId: process.env.KAFKA_GROUP_ID });

    await consumer.connect();
    this.logger.log('✅ Kafka Consumer connected');

    await consumer.subscribe({ topic: 'product.added', fromBeginning: true });

    this.logger.log('📩 Subscribed to topic: product.added');

    await consumer.run({
      eachMessage: async ({ topic, partition, message }) => {
        const payload = JSON.parse(message.value.toString());
        this.logger.log(`📨 Received message on "${topic}": ${JSON.stringify(payload, null, 2)}`);

        try {
          if (!payload.productname || !payload.category || !payload.manufacturer || !payload.subcategory) {
            this.logger.warn('⚠️ Missing required product fields. Skipping.');
            return;
          }

          await this.searchService.createOrUpdateProduct(payload);
          this.logger.log(`✅ Product stored in Typesense and sent to recommendations API`);
        } catch (error) {
          this.logger.error('❌ Failed to process product.added event:', error);
        }
      },
    });
  }
}
