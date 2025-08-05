// src/modules/order/order.service.ts
import { Injectable, Logger } from '@nestjs/common';
import axios from 'axios';
import { Order } from './order.model';
import { KafkaProducerService } from '../../kafka/producer.service';

@Injectable()
export class OrderService {
  private readonly logger = new Logger(OrderService.name);

  constructor(private readonly kafkaProducer: KafkaProducerService) {}

  async createOrderFromCart(userId: string, addressId?: string) {
  if (!userId) throw new Error('User ID is required');

  const cartUrl = `http://172.232.110.10:8005/cart/getallcartitems/${userId}`;
  const addressUrl = `http://172.232.110.10:8002/user/address/get`;
  const profileUrl = `http://172.232.110.10:8002/user/profile/get`;

  this.logger.log(`Fetching cart, address, and profile for user: ${userId}`);

  let cartRes, addressRes, profileRes;

  try {
    cartRes = await axios.get(cartUrl);
  } catch (err) {
    this.logger.error(`Cart service unavailable: ${err.message}`);
    throw new Error('Cart Service is not available');
  }

  try {
    addressRes = await axios.post(addressUrl, { userId });
  } catch (err) {
    this.logger.error(`Address service unavailable: ${err.message}`);
    throw new Error('Address Service is not available');
  }

  try {
    profileRes = await axios.post(profileUrl, { userId });
  } catch (err) {
    this.logger.error(`Profile service unavailable: ${err.message}`);
    throw new Error('Profile Service is not available');
  }

  const items = cartRes.data?.data?.items;
  const cartTotal = cartRes.data?.data?.cartTotal;
  const addressList = addressRes.data?.addresses;
  const profile = profileRes.data?.profile;

  if (!items || items.length === 0) throw new Error('Cart is empty');
  if (!addressList || addressList.length === 0) throw new Error('No address found for user');
  if (!profile) throw new Error('User profile not found');

  let selectedAddress;

  if (addressId) {
    selectedAddress = addressList.find((addr: any) => addr.addressId === addressId);
    if (!selectedAddress) {
      this.logger.warn(`Provided addressId ${addressId} not found. Falling back to default.`);
    }
  }

  if (!selectedAddress) {
    selectedAddress = addressList.find((addr: any) => addr.isDefault) || addressList[0];
  }

  const enrichedItems = items.map((item: any) => ({
    productId: item.productId,
    qty: item.quantity,
    price: item.price,
    totalPrice: item.totalPrice,
  }));

  try {
    const order = await Order.create({
      userId,
      items: enrichedItems,
      total: cartTotal,
      status: 'pending',
      deliveryAddress: {
        address: selectedAddress.address,
        pin: selectedAddress.pin,
        city: selectedAddress.city,
        state: selectedAddress.state,
      },
    });

    await this.kafkaProducer.produceEvent('order.created', order);

    this.logger.log(`Order created for user: ${userId}`);

    return {
      ...order.toJSON(),
      userProfile: {
        first_name: profile.first_name,
        last_name: profile.last_name,
        email: profile.email,
        phone: profile.phone,
      },
    };
  } catch (error) {
    this.logger.error(`Failed to create order in DB: ${error.message}`);
    throw new Error('Failed to create order');
  }
}


  async getOrderById(id: string) {
    const order = await Order.findByPk(id);
    if (!order) throw new Error('Order not found');

    const userProfile = await this.fetchUserProfile(order.userId);

    return {
      ...order.toJSON(),
      userProfile,
    };
  }

  async getOrdersByUser(userId: string) {
    const orders = await Order.findAll({ where: { userId } });
    const userProfile = await this.fetchUserProfile(userId);

    return orders.map(order => ({
      ...order.toJSON(),
      userProfile,
    }));
  }

  async updateOrderStatus(id: string, status: string) {
    const order = await Order.findByPk(id);
    if (!order) throw new Error('Order not found');

    order.status = status;
    await order.save();

    await this.kafkaProducer.produceEvent('order.status.updated', order);
    return order;
  }

  private async fetchUserProfile(userId: string) {
    try {
      const profileRes = await axios.post(`http://172.232.110.10:8002/user/profile/get`, { userId });
      const profile = profileRes.data?.profile;
      if (!profile) return null;

      return {
        first_name: profile.first_name,
        last_name: profile.last_name,
        email: profile.email,
        phone: profile.phone,
      };
    } catch (err) {
      this.logger.warn(`Unable to fetch profile for user ${userId}: ${err.message}`);
      return null;
    }
  }
}
