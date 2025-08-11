import { Injectable, Logger } from '@nestjs/common';
import axios from 'axios';
import { Order } from './order.model';
import { KafkaProducerService } from '../../kafka/producer.service';
import { CreateOrderDto } from './dto/create-order.dto';

@Injectable()
export class OrderService {
  private readonly logger = new Logger(OrderService.name);

  constructor(private readonly kafkaProducer: KafkaProducerService) {}

  async createOrderFromPayload(payload: CreateOrderDto) {
    const {
      userId,
      billingDetails,
      items,
      subtotal,
      gstAmount,
      shippingCharge,
      total
    } = payload;

    if (!userId) throw new Error('User ID is required');
    if (!billingDetails?.email) throw new Error('Billing details are required');
    if (!Array.isArray(items) || items.length === 0) throw new Error('Items list is required');

    // ✅ Validate cart with Cart Service
    const cartUrl = `http://172.232.110.10:8005/cart/getallcartitems/${userId}`;
    let cartRes;
    try {
      cartRes = await axios.get(cartUrl);
    } catch (err) {
      this.logger.error(`Cart service unavailable: ${err.message}`);
      throw new Error('Cart Service is not available');
    }

    const cartItems = cartRes.data?.data?.items || [];
    if (cartItems.length === 0) throw new Error('Cart is empty');

    for (const p of items) {
      const found = cartItems.find(
        (c: any) =>
          c.productId.toString().trim().toLowerCase() ===
            p.productId.toString().trim().toLowerCase() &&
          c.quantity >= p.qty,
      );
      if (!found) {
        throw new Error(`Product ${p.name} not found in cart or insufficient quantity`);
      }
    }

    try {
      // ✅ Step 1: Create order in DB
      const order = await Order.create({
        userId,
        items,
        subtotal,
        gstAmount,
        shippingCharge,
        total,
        billingDetails,
        status: 'pending'
      });

      //
      // ✅ Step 2: Create Razorpay order by calling Payment Service
      const paymentServiceUrl = `http://172.232.110.10:8007/payment/initiate`; 
      const paymentRes = await axios.post(paymentServiceUrl, {
  orderId: order.orderId, // ✅ Correct field
  userId: order.userId,
  total: order.total,
  items: order.items
});

    

      if (!paymentRes.data?.razorpayOrderId) {
        throw new Error('Failed to create Razorpay order');
      }

      // ✅ Step 3: Emit Kafka event
      await this.kafkaProducer.produceEvent('order.created', order.toJSON());

      this.logger.log(`Order created & payment initiated for user: ${userId}`);

      // ✅ Step 4: Return both order and payment details
      return {
        ...order.toJSON(),
        razorpayOrderId: paymentRes.data.razorpayOrderId,
        razorpayAmount: paymentRes.data.amount,
        currency: paymentRes.data.currency
      };
    } catch (error) {
      this.logger.error(`Failed to create order or payment: ${error.message}`);
      throw new Error(error.message || 'Failed to create order');
    }
  }

  async getOrderById(id: string) {
    const order = await Order.findByPk(id);
    if (!order) throw new Error('Order not found');

    return {
      ...order.toJSON(),
      deliveryAddress: order.billingDetails || {},
      items: Array.isArray(order.items) ? order.items : [],
    };
  }

  async getOrdersByUser(userId: string) {
    const orders = await Order.findAll({ where: { userId } });
    return orders.map((order) => order.toJSON());
  }

  async updateOrderStatus(id: string, status: string) {
    const order = await Order.findByPk(id);
    if (!order) throw new Error('Order not found');

    order.status = status;
    await order.save();

    await this.kafkaProducer.produceEvent('order.status.updated', order.toJSON());
    return order;
  }
}