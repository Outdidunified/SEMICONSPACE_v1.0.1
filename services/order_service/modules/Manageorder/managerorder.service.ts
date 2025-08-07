import {
  Injectable,
  HttpException,
  HttpStatus,
  Logger,
} from '@nestjs/common';
import { InjectModel } from '@nestjs/sequelize';
import { Op, fn, col, literal, Sequelize } from 'sequelize'; // Top of the file
import { ManagerOrder } from './managerorder.model';
import { UpdateManagerOrderDto } from './dto/update-managerorder.dto';
import axios from 'axios';
// This service handles order management operations, including fetching and updating orders.

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
          statusCode: 400,
          error: true,
          message: `Invalid ${label}`,
        },
        400,
      );
    }
  }

  private async fetchUserProfile(userId: string) {
    try {
      const profileRes = await axios.post(
        `http://172.232.110.10:8002/user/profile/get`,
        { userId },
      );
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

    const enriched = await Promise.all(
      data.map(async (order) => ({
        ...order.toJSON(),
        userProfile: await this.fetchUserProfile(order.userId),
      })),
    );

    return {
      statusCode: HttpStatus.OK,
      error: false,
      message: 'Orders fetched successfully',
      data: enriched,
    };
  }

  async findOne(orderId: string): Promise<any> {
    this.validateUUID(orderId, 'Order ID');

    const order = await this.orderModel.findByPk(orderId);
    if (!order) {
      throw new HttpException(
        {
          statusCode: 404,
          error: true,
          message: 'Order not found',
        },
        404,
      );
    }

    const userProfile = await this.fetchUserProfile(order.userId);

    return {
      statusCode: 200,
      error: false,
      message: 'Order fetched successfully',
      data: {
        ...order.toJSON(),
        userProfile,
      },
    };
  }

 async update(orderId: string, dto: UpdateManagerOrderDto): Promise<any> {
  this.validateUUID(orderId, 'Order ID');

  const existingOrder = await this.orderModel.findByPk(orderId);
  if (!existingOrder) {
    throw new HttpException({ statusCode: 404, error: true, message: 'Order not found' }, 404);
  }

  const now = new Date();

  // ✅ Automatically track time when status is updated
  switch (dto.status) {
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
  if (dto.totalAmount) existingOrder.total = dto.totalAmount;
  if (dto.deliveryAddress) {
    try {
      existingOrder.deliveryAddress = JSON.parse(dto.deliveryAddress);
    } catch {
      throw new HttpException({ statusCode: 400, error: true, message: 'Invalid address format' }, 400);
    }
  }

  await existingOrder.save();

  return {
    statusCode: 200,
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
            statusCode: 400,
            error: true,
            message: 'User ID is required',
          },
          400,
        );
      }

      this.validateUUID(userId, 'User ID');

      const orders = await this.orderModel.findAll({ where: { userId } });

      if (!orders || orders.length === 0) {
        return {
          statusCode: 404,
          error: true,
          message: `No orders found for user ID ${userId}`,
        };
      }

      const userProfile = await this.fetchUserProfile(userId);

      const enriched = orders.map((order) => ({
        ...order.toJSON(),
        userProfile,
      }));

      return {
        statusCode: 200,
        error: false,
        message: 'Orders fetched successfully',
        data: enriched,
      };
    } catch (error) {
      this.logger.error(' Error in findByUserId:', error);

      return {
        statusCode: error?.status || 500,
        error: true,
        message: error?.message || 'Unexpected error while fetching orders',
      };
    }
  }

  async getAnalytics() {
  try {
    // 1. Total Orders Count
    const totalOrders = await this.orderModel.count();

    // 2. Orders Count by Status
    const ordersByStatus = await this.orderModel.findAll({
      attributes: [
        'status',
        [fn('COUNT', col('status')), 'count']
      ],
      group: ['status'],
    });

    // 3. Monthly Orders (Last 6 Months)
    const monthlyOrders = await this.orderModel.findAll({
      attributes: [
        [fn('DATE_TRUNC', 'month', col('createdat')), 'month'],
        [fn('COUNT', '*'), 'count'],
      ],
      group: [literal('DATE_TRUNC(\'month\', "createdat")') as any],
      order: [[literal('DATE_TRUNC(\'month\', "createdat")'), 'DESC']],
      limit: 6,
    });

    // 4. Total Revenue Generated (only from delivered orders)
    const totalRevenue = await this.orderModel.sum('total', {
      where: {
        status: 'delivered',
      },
    });

    // 5. Average Order Value (AOV)
    const totalDeliveredOrders = await this.orderModel.count({
      where: { status: 'delivered' }
    });

    // 6. Orders Today / This Week / This Month
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    const ordersToday = await this.orderModel.count({
      where: {
        createdAt: {
          [Op.gte]: today,
        },
      },
    });

    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    
    const ordersThisWeek = await this.orderModel.count({
      where: {
        createdAt: {
          [Op.gte]: weekAgo,
        },
      },
    });

    const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
    
    const ordersThisMonth = await this.orderModel.count({
      where: {
        createdAt: {
          [Op.gte]: firstDayOfMonth,
        },
      },
    });

    // 7. Average Delivery Time
    const deliveryDurations = await this.orderModel.findAll({
      where: {
        deliveredAt: { [Op.ne]: null },
        confirmedAt: { [Op.ne]: null },
      },
      attributes: [
        [literal('EXTRACT(EPOCH FROM (deliveredat - confirmedat))'), 'duration_seconds'],
      ],
    });

 

    // Daily Revenue (existing)
    const daily = await this.orderModel.findAll({
      attributes: [
        [fn('DATE', col('createdat')), 'date'],
        [fn('SUM', col('total')), 'totalRevenue'],
        [fn('COUNT', col('orderId')), 'totalOrders'],
      ],
      group: [literal(`DATE("createdat")`) as any],
      order: [[literal('DATE("createdat")'), 'ASC']],
    });

    // Weekly Revenue (existing)
    const weekly = await this.orderModel.findAll({
      attributes: [
        [fn('DATE_TRUNC', 'week', col('createdat')), 'week'],
        [fn('SUM', col('total')), 'totalRevenue'],
        [fn('COUNT', col('orderId')), 'totalOrders'],
      ],
      group: [literal('DATE_TRUNC(\'week\', "createdat")') as any],
      order: [[literal('DATE_TRUNC(\'week\', "createdat")'), 'ASC']],
    });

    // Monthly Revenue (existing)
    const monthly = await this.orderModel.findAll({
      attributes: [
        [fn('DATE_TRUNC', 'month', col('createdat')), 'month'],
        [fn('SUM', col('total')), 'totalRevenue'],
        [fn('COUNT', col('orderId')), 'totalOrders'],
      ],
      group: [literal('DATE_TRUNC(\'month\', "createdat")') as any],
      order: [[literal('DATE_TRUNC(\'month\', "createdat")'), 'ASC']],
    });

    return {
      statusCode: 200,
      error: false,
      message: 'Order analytics fetched successfully',
      data: {
        // Summary Statistics
        totalOrders,
        totalRevenue: totalRevenue || 0,
        
        
        // Time-based Counts
        ordersToday,
        ordersThisWeek,
        ordersThisMonth,
        
        // Status Distribution
        ordersByStatus,
        
        // Time Series Data
        monthlyOrders,
        daily,
        weekly,
        monthly,
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
