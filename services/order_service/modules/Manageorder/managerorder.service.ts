import {
  Injectable,
  HttpException,
  HttpStatus,
  Logger,
} from '@nestjs/common';
import { InjectModel } from '@nestjs/sequelize';
import { ManagerOrder } from './managerorder.model';
import { UpdateManagerOrderDto } from './dto/update-managerorder.dto';

@Injectable()
export class ManagerOrderService {
  private readonly logger = new Logger(ManagerOrderService.name);

  constructor(
    @InjectModel(ManagerOrder)
    private readonly orderModel: typeof ManagerOrder,
  ) {}

  private validateUUID(uuid: string, label = 'ID') {
    const uuidRegex =
      /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

    if (!uuidRegex.test(uuid)) {
      throw new HttpException(
        {
          statusCode: HttpStatus.BAD_REQUEST,
          error: true,
          message: `Invalid ${label}`,
        },
        HttpStatus.BAD_REQUEST,
      );
    }
  }

  async findAll(): Promise<any> {
    const data = await this.orderModel.findAll();

    if (!data || data.length === 0) {
      throw new HttpException(
        {
          statusCode: HttpStatus.NOT_FOUND,
          error: true,
          message: 'No orders found',
        },
        HttpStatus.NOT_FOUND,
      );
    }

    return {
      statusCode: HttpStatus.OK,
      error: false,
      message: 'Orders fetched successfully',
      data: data.map(order => order.toJSON()),
    };
  }

  async findOne(orderId: string): Promise<any> {
    this.validateUUID(orderId, 'Order ID');

    const order = await this.orderModel.findByPk(orderId);
    if (!order) {
      throw new HttpException(
        {
          statusCode: HttpStatus.NOT_FOUND,
          error: true,
          message: 'Order not found',
        },
        HttpStatus.NOT_FOUND,
      );
    }

    return {
      statusCode: HttpStatus.OK,
      error: false,
      message: 'Order fetched successfully',
      data: order.toJSON(),
    };
  }

  async update(orderId: string, dto: UpdateManagerOrderDto): Promise<any> {
    this.validateUUID(orderId, 'Order ID');

    const existingOrder = await this.orderModel.findByPk(orderId);
    if (!existingOrder) {
      throw new HttpException(
        { statusCode: HttpStatus.NOT_FOUND, error: true, message: 'Order not found' },
        HttpStatus.NOT_FOUND,
      );
    }

    const now = new Date();

    switch (dto.status?.toLowerCase()) {
      case 'shipped':
        existingOrder.shippedAt = now;
        break;
      case 'out for delivery':
      case 'out-for-delivery':
        existingOrder.outForDeliveryAt = now;
        break;
      case 'delivered':
        existingOrder.deliveredAt = now;
        break;
    }

    if (dto.status) existingOrder.status = dto.status;
    if (dto.totalAmount !== undefined) existingOrder.total = dto.totalAmount;

    if (dto.deliveryAddress) {
      try {
        existingOrder.billingDetails = JSON.parse(dto.deliveryAddress);
      } catch {
        throw new HttpException(
          { statusCode: HttpStatus.BAD_REQUEST, error: true, message: 'Invalid address format' },
          HttpStatus.BAD_REQUEST,
        );
      }
    }

    await existingOrder.save();

    return {
      statusCode: HttpStatus.OK,
      error: false,
      message: 'Order updated successfully',
      data: existingOrder,
    };
  }

  async findByUserId(userId: string): Promise<any> {
    try {
      if (!userId) {
        throw new HttpException(
          {
            statusCode: HttpStatus.BAD_REQUEST,
            error: true,
            message: 'User ID is required',
          },
          HttpStatus.BAD_REQUEST,
        );
      }

      this.validateUUID(userId, 'User ID');

      const orders = await this.orderModel.findAll({ where: { userId } });

      if (!orders || orders.length === 0) {
        return {
          statusCode: HttpStatus.NOT_FOUND,
          error: true,
          message: `No orders found for user ID ${userId}`,
        };
      }

      return {
        statusCode: HttpStatus.OK,
        error: false,
        message: 'Orders fetched successfully',
        data: orders.map(order => order.toJSON()),
      };
    } catch (error) {
      this.logger.error('Error in findByUserId:', error);

      return {
        statusCode: error?.status || HttpStatus.INTERNAL_SERVER_ERROR,
        error: true,
        message: error?.message || 'Unexpected error while fetching orders',
      };
    }
  }
}
