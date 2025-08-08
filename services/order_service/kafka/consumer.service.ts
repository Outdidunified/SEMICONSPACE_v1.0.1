import { Injectable, OnModuleInit } from '@nestjs/common';
import { Kafka } from 'kafkajs';
import axios from 'axios';
import { Order } from '../modules/order/order.model';
import { OrderService } from '../modules/order/order.service';

@Injectable()
export class KafkaConsumerService implements OnModuleInit {
  constructor(private readonly orderService: OrderService) {}

  async onModuleInit() {
    const kafka = new Kafka({ brokers: [process.env.KAFKA_BROKER!] });
    const consumer = kafka.consumer({ groupId: 'order-group' });

    await consumer.connect();
    await consumer.subscribe({ topic: 'payment.success', fromBeginning: false });

    await consumer.run({
      eachMessage: async ({ topic, message }) => {
        if (topic === 'payment.success') {
          const data = JSON.parse(message.value.toString());
          const { orderId, razorpayOrderId, razorpayPaymentId } = data;

          const order = await Order.findByPk(orderId);
          if (!order) return;

          order.status = 'confirmed';
          order.razorpayOrderId = razorpayOrderId;
          order.razorpayPaymentId = razorpayPaymentId;
          await order.save();

          console.log(` Order ${orderId} marked as confirmed with Razorpay IDs.`);

          // Fetch full order with profile and address
          const fullOrder = await this.orderService.getOrderById(orderId);
          const { userProfile, deliveryAddress, items } = fullOrder;

          // Safety defaults (but no static values)
          const shipping_phone = userProfile?.phone || null;
          const shipping_zipcode = deliveryAddress?.pin || null;
          const shipping_address = deliveryAddress?.address || null;
          const shipping_city = deliveryAddress?.city || null;
          const shipping_state = deliveryAddress?.state || null;
          const shipping_firstname = userProfile?.first_name || null;
          const shipping_lastname = userProfile?.last_name || null;

          const products = Array.isArray(items)
            ? items.map((item) => ({
                product: `Product-${item.productId}`,
price: ((item.totalPrice ?? item.totalprice) / item.qty).toFixed(2),
                product_code: item.productId,
                product_quantity: String(item.qty),
                discount: item.discount || "0",
                tax_rate: item.taxRate || "0", // If available in item
                tax_title: item.taxTitle || null, // Optional
              }))
            : [];

          const payload: any = {
            order_id: fullOrder.orderId,
            products,
            payment_type: "PrePaid", // Assuming it's always prepaid. Adjust if needed.
            ewaybill: "NA",
            shipping_country: "India",
            shipping_phone,
            shipping_zipcode,
            shipping_address,
            shipping_city,
            shipping_state,
            shipping_firstname,
            shipping_lastname,
            order_date: new Date(fullOrder.createdAt)
              .toISOString()
              .slice(0, 19)
              .replace("T", " "),
            shipping: fullOrder.shippingFee ?? 0,
            order_total: fullOrder.total,
            taxes: fullOrder.taxes ?? 0,
            // Optional box dimensions if available
            order_weight: fullOrder.weight ?? null,
            box_length: fullOrder.length ?? null,
            box_breadth: fullOrder.breadth ?? null,
            box_height: fullOrder.height ?? null,
          };

          // Clean null/undefined keys from payload
          Object.keys(payload).forEach(
            (key) =>
              (payload[key] === null || payload[key] === undefined) &&
              delete payload[key],
          );

          try {
            const res = await axios.post('http://192.168.1.25:8010/shipway/receive-order', payload);
            console.log(` Sent order ${orderId} to Shipway. Response:`, res.data);
          } catch (error) {
            console.error(` Failed to send order ${orderId} to Shipway:`, error.message);
          }
        }
      },
    });
  }
}
