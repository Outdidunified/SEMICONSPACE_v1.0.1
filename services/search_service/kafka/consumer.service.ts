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
      brokers: [process.env.KAFKA_BROKER], // e.g., "localhost:9092"
    });

    const consumer = kafka.consumer({ groupId: process.env.KAFKA_GROUP_ID });

    await consumer.connect();
    this.logger.log('✅ Kafka Consumer connected');

    await consumer.subscribe({ topic: 'product.created', fromBeginning: true });
    await consumer.subscribe({ topic: 'product.updated', fromBeginning: true });
    await consumer.subscribe({ topic: 'product.activate_deactivate', fromBeginning: true });

    this.logger.log('📩 Subscribed to topics: product.created, product.updated, product.activate_deactivate');

    await consumer.run({
      eachMessage: async ({ topic, partition, message }) => {
        const payload = JSON.parse(message.value.toString());

        this.logger.log(`📨 Received message on topic "${topic}" (partition ${partition}): ${JSON.stringify(payload, null, 2)}`);

        try {
          const product = payload.product;

          if (!product) {
            this.logger.warn('⚠️ No "product" field found in Kafka message. Skipping.');
            return;
          }

          if (['product.created', 'product.updated', 'product.activate_deactivate'].includes(topic)) {
            await this.searchService.createOrUpdateProduct(product);
            this.logger.log(`✅ Product synced to Typesense (topic: ${topic})`);
          }
        } catch (error) {
          this.logger.error('❌ Failed to process product event:', error);
        }
      },
    });
  }
}
