import {
  Injectable,
  HttpException,
  HttpStatus,
  Logger,
} from '@nestjs/common';
import { InjectModel } from '@nestjs/sequelize';
import { ManagerOrder } from './managerorder.model';
import { UpdateManagerOrderDto } from './dto/update-managerorder.dto';
import axios from 'axios';

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
      throw new HttpException(
        {
          statusCode: 404,
          error: true,
          message: 'Order not found',
        },
        404,
      );
    }

    if (dto.status && dto.status === existingOrder.status) {
      return {
        statusCode: 409,
        error: true,
        message: `Order status is already '${dto.status}'`,
      };
    }

    const [count, updated] = await this.orderModel.update(dto, {
      where: { orderId },
      returning: true,
    });

    if (count === 0) {
      throw new HttpException(
        {
          statusCode: 404,
          error: true,
          message: 'Order not found or no changes made',
        },
        404,
      );
    }

    return {
      statusCode: 200,
      error: false,
      message: 'Order updated successfully',
      data: updated[0],
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
}
