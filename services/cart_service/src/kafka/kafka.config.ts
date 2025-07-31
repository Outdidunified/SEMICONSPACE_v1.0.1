import { KafkaOptions, Transport } from '@nestjs/microservices';

export const kafkaConfig: KafkaOptions = {
  transport: Transport.KAFKA,
  options: {
    client: {
        brokers: ['172.235.17.60:9092'], // 👈 external Kafka IP
    },
    consumer: {
      groupId: 'cart-consumer', // 👈 Unique per service
    },
  },
};
