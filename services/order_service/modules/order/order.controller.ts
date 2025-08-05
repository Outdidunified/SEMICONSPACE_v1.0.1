// src/modules/order/order.controller.ts

import {
  Controller,
  Post,
  Get,
  Body,
  Param,
  HttpException,
  HttpStatus,
  Logger,
  HttpCode,
  UsePipes,
  ValidationPipe,
} from '@nestjs/common';
import { OrderService } from './order.service';

@Controller('order') // ✅ Required since Gateway forwards to /order/*
export class OrderController {
  private readonly logger = new Logger(OrderController.name);

  constructor(private readonly orderService: OrderService) {}

  /**
   * Route: POST /order/createorder
   */
 // POST /order/createorder
@Post('createorder')
@HttpCode(HttpStatus.OK)
@UsePipes(new ValidationPipe({ transform: true }))
async placeOrder(@Body('userId') userId: string, @Body('addressId') addressId?: string) {
  if (!userId) {
    throw new HttpException({ error: true, message: 'User ID is required' }, HttpStatus.BAD_REQUEST);
  }

  this.logger.log(`Placing order for userId: ${userId}, using addressId: ${addressId}`);
  try {
    const order = await this.orderService.createOrderFromCart(userId, addressId);
    return { error: false, order };
  } catch (error) {
    this.logger.error('Order placement failed:', error.message);
    throw new HttpException(
      { error: true, message: error.message || 'Order placement failed' },
      HttpStatus.BAD_REQUEST,
    );
  }
}


  @Post('user-orders')
@HttpCode(HttpStatus.OK)
async getOrdersByUserPost(@Body('userId') userId: string) {
  if (!userId) {
    throw new HttpException({ error: true, message: 'User ID is required' }, HttpStatus.BAD_REQUEST);
  }

  try {
    const orders = await this.orderService.getOrdersByUser(userId);
    return { error: false, orders };
  } catch (error) {
    this.logger.error('Failed to fetch orders for user:', error.message);
    throw new HttpException(
      { error: true, message: error.message || 'Failed to fetch user orders' },
      HttpStatus.INTERNAL_SERVER_ERROR,
    );
  }
}

  /**
   * Route: GET /order/:orderId
   */
  @Get(':orderId')
  @HttpCode(HttpStatus.OK)
  async getOrder(@Param('orderId') orderId: string) {
    if (!orderId) {
      throw new HttpException({ error: true, message: 'Order ID is required' }, HttpStatus.BAD_REQUEST);
    }

    try {
      const order = await this.orderService.getOrderById(orderId);
      if (!order) {
        throw new HttpException({ error: true, message: 'Order not found' }, HttpStatus.NOT_FOUND);
      }

      return { error: false, order };
    } catch (error) {
      this.logger.error('Failed to fetch order:', error.message);
      throw new HttpException(
        { error: true, message: error.message || 'Failed to fetch order' },
        HttpStatus.INTERNAL_SERVER_ERROR,
      );
    }
  }
}
