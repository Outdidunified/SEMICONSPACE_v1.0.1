// services/order_service/kafka/consumer.service.ts
// This file is part of the Order Service for handling Kafka events related to orders.
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

      console.log('📩 Received payment.success event:', {
        orderId,
        razorpayOrderId,
        razorpayPaymentId,
      });

      const order = await Order.findByPk(orderId);

      if (order) {
        const confirmedAt = new Date();

        console.log('🛠️ Attempting to update order:', {
          status: 'confirmed',
          razorpayOrderId,
          razorpayPaymentId,
          confirmedAt,
        });

        const [affectedRows] = await Order.update(
          {
            status: 'confirmed',
            razorpayOrderId,
            razorpayPaymentId,
            confirmedAt,
          },
          {
            where: { orderId },
          },
        );

        console.log(`📝 Rows affected: ${affectedRows}`);

        const updatedOrder = await Order.findByPk(orderId);

        console.log('✅ Updated order:', {
          status: updatedOrder?.status,
          confirmedAt: updatedOrder?.confirmedAt,
          updatedAt: updatedOrder?.updatedAt,
        });
      } else {
        console.log(`❌ Order not found for orderId: ${orderId}`);
      }
    }
  },
});



  }
}
