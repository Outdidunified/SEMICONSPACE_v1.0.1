import {
  Controller,
  Post,
  Body,
  Get,
  Param,
  HttpException,
  HttpStatus,
} from '@nestjs/common';
import { ConfirmPaymentDto } from '../dto/confirm-payment.dto';
import { PaymentService } from './payment.service';

@Controller('payment')
export class PaymentController {
  constructor(private readonly paymentService: PaymentService) {}

  // ✅ Endpoint to initiate payment
  @Post('initiate')
  async initiatePayment(@Body() order: any) {
    try {
      return await this.paymentService.initiatePayment(order);
    } catch (err) {
      throw new HttpException(
        { error: true, message: err.message || 'Payment initiation failed' },
        HttpStatus.BAD_REQUEST,
      );
    }
  }

  // ✅ Endpoint to confirm payment
  @Post('confirm')
  async confirm(@Body() dto: ConfirmPaymentDto) {
    try {
      return await this.paymentService.confirmPayment(dto);
    } catch (err) {
      throw new HttpException(
        { error: true, message: err.message || 'Payment confirmation failed' },
        HttpStatus.BAD_REQUEST,
      );
    }
  }

  // ✅ Endpoint to get Razorpay order details
  @Get('razorpay-order/:orderId')
  async getRazorpayOrder(@Param('orderId') orderId: string) {
    try {
      return await this.paymentService.getRazorpayOrder(orderId);
    } catch (err) {
      throw new HttpException(
        { error: true, message: err.message || 'Payment order not found' },
        HttpStatus.NOT_FOUND,
      );
    }
  }
}
