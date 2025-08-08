import { Injectable, Logger } from '@nestjs/common';
import axios from 'axios';
import { Order } from './order.model';
import { KafkaProducerService } from '../../kafka/producer.service';
import { CreateOrderDto } from './dto/create-order.dto';

@Injectable()
export class OrderService {
  private readonly logger = new Logger(OrderService.name);

  constructor(private readonly kafkaProducer: KafkaProducerService) {}

  /**
   * Creates an order from frontend payload but validates against Cart Service
   */
  async createOrderFromPayload(payload: CreateOrderDto) {
    const {
      userId,
      billingDetails,
      items,
      subtotal,
      gstAmount,
      shippingCharge,
      total,
      razorpayOrderId,
      razorpayPaymentId,
      // Removed status from destructuring intentionally
    } = payload;

    if (!userId) throw new Error('User ID is required');
    if (!billingDetails?.email) throw new Error('Billing details are required');
    if (!Array.isArray(items) || items.length === 0) throw new Error('Items list is required');

    // 1️⃣ Validate cart items with Cart Service
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

    // 2️⃣ Check that all requested products are in the cart
    for (const p of items) {
      const found = cartItems.find(
        (c: any) => c.productId === p.productId && c.quantity >= p.qty,
      );
      if (!found) {
        throw new Error(`Product ${p.name} not found in cart or insufficient quantity`);
      }
    }

    // 3️⃣ Create the order in DB with status always 'pending'
    try {
      const order = await Order.create({
        userId,
        items,
        subtotal,
        gstAmount,
        shippingCharge,
        total,
        razorpayOrderId,
        razorpayPaymentId,
        status: 'pending',  // <-- Force status to 'pending' here
        billingDetails,
      });

      // 4️⃣ Emit Kafka event
      await this.kafkaProducer.produceEvent('order.created', order.toJSON());

      this.logger.log(`Order created for user: ${userId}`);
      return order.toJSON();
    } catch (error) {
      this.logger.error(`Failed to create order in DB: ${error.message}`);
      throw new Error('Failed to create order');
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
