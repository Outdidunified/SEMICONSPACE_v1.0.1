// services/order_service/kafka/consumer.service.ts

import { Injectable, OnModuleInit } from '@nestjs/common';
import { Kafka } from 'kafkajs';
import { Order } from '../modules/order/order.model';

@Injectable()
export class KafkaConsumerService implements OnModuleInit {
  async onModuleInit() {
    const kafka = new Kafka({ brokers: [process.env.KAFKA_BROKER!] });
    const consumer = kafka.consumer({ groupId: 'order-group' });

    await consumer.connect();
    await consumer.subscribe({ topic: 'payment.success', fromBeginning: false });

    // kafka/consumer.service.ts
await consumer.run({
  eachMessage: async ({ topic, partition, message }) => {
    if (topic === 'payment.success') {
      const data = JSON.parse(message.value.toString());
      const { orderId, razorpayOrderId, razorpayPaymentId } = data;

      const order = await Order.findByPk(orderId);
      if (order) {
        order.status = 'confirmed';
        order.razorpayOrderId = razorpayOrderId;
        order.razorpayPaymentId = razorpayPaymentId;
        await order.save();

        console.log(`✅ Order ${orderId} marked as confirmed with Razorpay IDs.`);
      }
    }
  },
});

  }
}
