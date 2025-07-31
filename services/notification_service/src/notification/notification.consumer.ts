import { Controller } from '@nestjs/common';
import { MessagePattern, Payload } from '@nestjs/microservices';
import { NotificationService } from './notification.service';

@Controller()
export class NotificationConsumer {
  constructor(private readonly notificationService: NotificationService) {}

  @MessagePattern('user.registered')
  async handleUserRegistered(@Payload() payload: any) {
    const timestamp = new Date().toISOString();

    await this.notificationService.sendNotification({
      toEmail: payload.email,
      type: 'email',
      message: `Welcome ${payload.first_name}! Thanks for registering.`,
      userId: payload.userId,
      notificationId: Date.now(),
      status: 'sent',
      timestamp,
    });
  }

  @MessagePattern('user.loggedin')
  async handleUserLoggedIn(@Payload() payload: any) {
    const timestamp = new Date().toISOString();

    if (!payload.email || !payload.userId) {
      console.warn('❌ Missing fields in login payload:', payload);
      return;
    }

    await this.notificationService.sendNotification({
      toEmail: payload.email,
      type: 'email',
      message: `Hi! You just logged in at ${payload.time}`,
      userId: payload.userId,
      notificationId: Date.now(),
      phone: payload.phone,
      status: 'sent',
      timestamp,
      subject: 'Login Alert',
      channel: 'email',
      sender: 'notification-service',
    });
  }

  @MessagePattern('order.created')
  async handleOrderCreated(@Payload() payload: any) {
    try {
      console.log('📦 Kafka - order.created:', payload);

      const order = payload;
      const timestamp = new Date().toISOString();

      const itemSummary = Array.isArray(order.items)
        ? order.items.map((item, i) => `Item ${i + 1}: Product ID ${item.productId} | Qty: ${item.qty} | Price: $${item.price}`).join(', ')
        : 'Order items unavailable';

      const message = `
        Your order (${order.orderId}) has been placed successfully.<br/>
        Total Amount: $${order.total}<br/>
        Status: ${order.status}<br/>
        Items: ${itemSummary}
      `;

      await this.notificationService.sendNotification({
        toEmail: payload.email || 'user@domain.com',
        type: 'email',
        message,
        userId: order.userId,
        notificationId: Date.now(),
        status: 'sent',
        timestamp,
        subject: 'Your Order Confirmation',
        channel: 'email',
        sender: 'notification-service',
      });
    } catch (error) {
      console.error('❌ Error in handleOrderCreated:', error);
    }
  }
}