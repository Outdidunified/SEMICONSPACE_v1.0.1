// services/payment_service/modules/payment/payment.service.ts
import { Injectable, Logger } from '@nestjs/common';
import { Payment } from './payment.model';
import { ConfirmPaymentDto } from '../dto/confirm-payment.dto';
import { KafkaProducerService } from '../../kafka/producer.service';
import Razorpay = require('razorpay');
import * as dotenv from 'dotenv';

dotenv.config(); // Load environment variables before Razorpay

const razorpay = new Razorpay({
    key_id: process.env.RAZORPAY_KEY_ID!,
    key_secret: process.env.RAZORPAY_KEY_SECRET!,
});

@Injectable()
export class PaymentService {
    private readonly logger = new Logger(PaymentService.name);

    constructor(private readonly kafkaProducer: KafkaProducerService) {}

    async initiatePayment(order: any) {
        this.logger.log('Initiating payment for order:', order);

        let totalInRupees = Number(order.total);
        if (isNaN(totalInRupees) || totalInRupees < 1) {
            this.logger.error(`Invalid order total received: ${order.total}`);
            throw new Error('Invalid order total: must be at least ₹1');
        }

        // Fix to 2 decimal places
        totalInRupees = Number(totalInRupees.toFixed(2));

        try {
            const rzpOrder = await razorpay.orders.create({
                amount: totalInRupees, // Keep total in rupees
                currency: 'INR',
                receipt: String(order.orderId),
            });

            this.logger.log(`Razorpay order created: ${rzpOrder.id}`);

            await Payment.create({
                orderId: order.orderId,
                userId: order.userId,
                razorpayOrderId: rzpOrder.id,
                razorpayPaymentId: '',
                status: 'pending',
                total: totalInRupees, // store in rupees with 2 decimals
                items: order.items.map((item) => ({
                    productId: item.productId,
                    qty: item.qty,
                    totalprice: Number((item.totalPrice ?? item.price * item.qty).toFixed(2)),
                })),
            });

            this.logger.log(`Payment record created for order: ${order.orderId}`);

            return {
                razorpayOrderId: rzpOrder.id,
                orderId: order.orderId,
                userId: order.userId,
                amount: totalInRupees,
                currency: 'INR',
            };
        } catch (err: any) {
            this.logger.error('Razorpay order creation failed:', err.message, err);
            throw new Error(err?.description || err.message || 'Failed to create Razorpay order');
        }
    }

    async confirmPayment(dto: ConfirmPaymentDto) {
        const { razorpayOrderId, razorpayPaymentId } = dto;

        const payment = await Payment.findOne({ where: { razorpayOrderId } });
        if (!payment) throw new Error('Payment record not found');

        payment.status = 'success';
        payment.razorpayPaymentId = razorpayPaymentId;
        await payment.save();

        await this.kafkaProducer.produceEvent('payment.success', {
            orderId: payment.orderId,
            userId: payment.userId,
            razorpayOrderId: payment.razorpayOrderId,
            razorpayPaymentId: razorpayPaymentId,
            status: 'success',
            total: payment.total,
            createdAt: payment.createdAt,
            items: payment.items.map((item) => ({
                productId: item.productId,
                qty: item.qty,
                totalprice: item.totalprice,
            })),
        });

        return {
            success: true,
            message: 'Payment confirmed successfully',
            data: {
                orderId: payment.orderId,
                userId: payment.userId,
                paymentId: razorpayPaymentId,
                razorpayOrderId: payment.razorpayOrderId,
                total: payment.total,
                status: payment.status,
                createdAt: payment.createdAt,
                items: payment.items.map((item) => ({
                    productId: item.productId,
                    qty: item.qty,
                    totalprice: item.totalprice,
                })),
            },
        };
    }

    async getRazorpayOrder(orderId: string) {
        const payment = await Payment.findOne({ where: { orderId } });

        if (!payment) {
            throw new Error('Razorpay Order not found');
        }

        return {
            razorpayOrderId: payment.razorpayOrderId,
            orderId: payment.orderId,
            userId: payment.userId,
            amount: payment.total, // already fixed to 2 decimals
            currency: 'INR',
        };
    }
}
