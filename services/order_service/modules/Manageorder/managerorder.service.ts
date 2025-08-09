import {
  Injectable,
  HttpException,
  HttpStatus,
  Logger,
} from '@nestjs/common';
import { InjectModel } from '@nestjs/sequelize';
import { Op, fn, col, literal, Sequelize } from 'sequelize';
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
        { statusCode: HttpStatus.NOT_FOUND, error: true, message: 'No orders found' },
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
        { statusCode: HttpStatus.NOT_FOUND, error: true, message: 'Order not found' },
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
          { statusCode: HttpStatus.BAD_REQUEST, error: true, message: 'User ID is required' },
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

  async getAnalytics() {
  try {
    const totalOrders = await this.orderModel.count();

    const ordersByStatus = await this.orderModel.findAll({
      attributes: ['status', [fn('COUNT', col('status')), 'count']],
      group: ['status'],
    });

    const monthlyOrders = await this.orderModel.findAll({
      attributes: [
        [fn('DATE_TRUNC', 'month', col('createdAt')), 'month'],
        [fn('COUNT', '*'), 'count'],
      ],
      group: [literal('DATE_TRUNC(\'month\', "createdAt")') as any],
      order: [[literal('DATE_TRUNC(\'month\', "createdAt")'), 'DESC']],
      limit: 6,
    });

    const totalRevenue = await this.orderModel.sum('total', {
      where: { status: 'delivered' },
    });

    const ordersToday = await this.orderModel.count({
      where: { createdAt: { [Op.gte]: new Date(new Date().setHours(0, 0, 0, 0)) } },
    });

    const ordersThisWeek = await this.orderModel.count({
      where: { createdAt: { [Op.gte]: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000) } },
    });

    const ordersThisMonth = await this.orderModel.count({
      where: {
        createdAt: {
          [Op.gte]: new Date(new Date().getFullYear(), new Date().getMonth(), 1),
        },
      },
    });

    const daily = await this.orderModel.findAll({
      attributes: [
        [fn('DATE', col('createdAt')), 'date'],
        [fn('SUM', col('total')), 'totalRevenue'],
        [fn('COUNT', col('orderId')), 'totalOrders'],
      ],
      group: [literal(`DATE("createdAt")`) as any],
      order: [[literal('DATE("createdAt")'), 'ASC']],
    });

    const weekly = await this.orderModel.findAll({
      attributes: [
        [fn('DATE_TRUNC', 'week', col('createdAt')), 'week'],
        [fn('SUM', col('total')), 'totalRevenue'],
        [fn('COUNT', col('orderId')), 'totalOrders'],
      ],
      group: [literal('DATE_TRUNC(\'week\', "createdAt")') as any],
      order: [[literal('DATE_TRUNC(\'week\', "createdAt")'), 'ASC']],
    });

    const monthly = await this.orderModel.findAll({
      attributes: [
        [fn('DATE_TRUNC', 'month', col('createdAt')), 'month'],
        [fn('SUM', col('total')), 'totalRevenue'],
        [fn('COUNT', col('orderId')), 'totalOrders'],
      ],
      group: [literal('DATE_TRUNC(\'month\', "createdAt")') as any],
      order: [[literal('DATE_TRUNC(\'month\', "createdAt")'), 'ASC']],
    });

    // ✅ Yearly Analytics
    const yearly = await this.orderModel.findAll({
      attributes: [
        [fn('DATE_TRUNC', 'year', col('createdAt')), 'year'],
        [fn('SUM', col('total')), 'totalRevenue'],
        [fn('COUNT', col('orderId')), 'totalOrders'],
      ],
      group: [literal('DATE_TRUNC(\'year\', "createdAt")') as any],
      order: [[literal('DATE_TRUNC(\'year\', "createdAt")'), 'ASC']],
    });

    return {
      statusCode: 200,
      error: false,
      message: 'Order analytics fetched successfully',
      data: {
        totalOrders,
        totalRevenue: totalRevenue || 0,
        ordersToday,
        ordersThisWeek,
        ordersThisMonth,
        ordersByStatus,
        monthlyOrders,
        daily,
        weekly,
        monthly,
        yearly, // Added yearly analytics to response
      },
    };
  } catch (error) {
    this.logger.error('Error in getAnalytics:', error);
    return {
      statusCode: 500,
      error: true,
      message: 'Failed to fetch analytics',
    };
  }
}

}
