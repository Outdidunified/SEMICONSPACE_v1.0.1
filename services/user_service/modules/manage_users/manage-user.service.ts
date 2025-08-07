import { Injectable, HttpException, HttpStatus } from '@nestjs/common';
import { InjectModel } from '@nestjs/sequelize';
import { ManageUser } from './manage-user.model';
import { Profile } from '../../models/profile.model';
import { CreateManageUserDto } from './dto/create-manage-user.dto';
import { UpdateManageUserDto } from './dto/update-manage-user.dto';
import { ProducerService } from '../../kafka/producer.service';
import { Op } from 'sequelize';

@Injectable()
export class ManageUserService {
  constructor(
    @InjectModel(ManageUser)
    private readonly userModel: typeof ManageUser,
    @InjectModel(Profile)
    private readonly profileModel: typeof Profile,
    private readonly producerService: ProducerService,
  ) {}

  // ✅ Create user in users table and emit Kafka
  async create(dto: CreateManageUserDto) {
    try {
      const existingUser = await this.userModel.findOne({
        where: {
          [Op.or]: [{ email: dto.email }, { phone: dto.phone }],
        },
      });

      if (existingUser) {
        const errors = [];
        if (existingUser.email === dto.email) errors.push('Email already exists');
        if (existingUser.phone === dto.phone) errors.push('Phone number already exists');
        return {
          statusCode: HttpStatus.CONFLICT,
          error: true,
          message: errors.join(' and '),
        };
      }

      const new_user = await this.userModel.create({
        ...dto,
        created_at: new Date(),
      });

      await this.producerService.produceEvent('user.registered', {
        userId: new_user.userId,
        first_name: new_user.first_name,
        last_name: new_user.last_name,
        email: new_user.email,
        phone: new_user.phone,
        password: new_user.password,
        role: new_user.role,
        role_id: new_user.role_id,
        created_at: new_user.created_at?.toISOString(),
        created_by: new_user.created_by,
        modified_at: new_user.modified_at?.toISOString() || null,
        modified_by: new_user.modified_by || null,
      });

      return {
        statusCode: HttpStatus.CREATED,
        error: false,
        message: 'User created successfully',
        data: new_user,
      };
    } catch (error) {
      return {
        statusCode: HttpStatus.BAD_REQUEST,
        error: true,
        message: 'User creation failed: ' + (error.message || 'Unknown error'),
      };
    }
  }

  // 🔍 Get all profiles from profile_details table
  async findAll() {
    try {
      const allProfiles = await this.profileModel.findAll({ order: [['created_at', 'DESC']] });
      return {
        statusCode: HttpStatus.OK,
        error: false,
        message: 'Profiles fetched successfully',
        data: allProfiles,
      };
    } catch (error) {
      return {
        statusCode: HttpStatus.INTERNAL_SERVER_ERROR,
        error: true,
        message: 'Failed to fetch profiles',
      };
    }
  }

  // 🔍 Get single profile by userId
  async findOne(userId: string) {
    try {
      const profile = await this.profileModel.findByPk(userId);
      if (!profile) {
        return {
          statusCode: HttpStatus.NOT_FOUND,
          error: true,
          message: 'Profile not found',
        };
      }
      return {
        statusCode: HttpStatus.OK,
        error: false,
        message: 'Profile fetched successfully',
        data: profile,
      };
    } catch (error) {
      return {
        statusCode: HttpStatus.INTERNAL_SERVER_ERROR,
        error: true,
        message: 'Failed to fetch profile',
      };
    }
  }

  // 📦 Add to manage-user.service.ts

async getUserStats() {
  try {
    const total = await this.profileModel.count();
    const active = await this.profileModel.count({ where: { status: true } });
    const inactive = await this.profileModel.count({ where: { status: false } });

    return {
      statusCode: HttpStatus.OK,
      error: false,
      message: 'User stats fetched successfully',
      data: {
        total,
        active,
        inactive,
      },
    };
  } catch (error) {
    return {
      statusCode: HttpStatus.INTERNAL_SERVER_ERROR,
      error: true,
      message: 'Failed to fetch user stats',
    };
  }
}


  // ✏️ Update user
async update(userId: string, dto: UpdateManageUserDto & { modified_by: string }) {
  try {
    const profile = await this.profileModel.findByPk(userId);
    if (!profile) {
      return {
        statusCode: HttpStatus.NOT_FOUND,
        error: true,
        message: 'Profile not found',
      };
    }

    // Check email immutability
    if (dto.email && dto.email !== profile.email) {
      return {
        statusCode: HttpStatus.BAD_REQUEST,
        error: true,
        message: 'Email cannot be updated',
      };
    }

    // Check phone number uniqueness
    if (dto.phone && dto.phone !== profile.phone) {
      const exists = await this.profileModel.findOne({
        where: {
          phone: dto.phone,
          userId: { [Op.ne]: userId },
        },
      });
      if (exists) {
        return {
          statusCode: HttpStatus.CONFLICT,
          error: true,
          message: 'Phone number already in use',
        };
      }
    }

    // Detect changes in general fields
    const isModified = [
      'first_name',
      'last_name',
      'phone',
      'password',
      'role',
      'role_id',
    ].some((key) => dto[key] !== undefined && dto[key] !== profile[key]);

    // Detect status change
    const isStatusModified =
      typeof dto.status === 'boolean' && dto.status !== profile.status;

    if (!isModified && !isStatusModified) {
      return {
        statusCode: HttpStatus.BAD_REQUEST,
        error: true,
        message: 'No changes detected',
      };
    }

    // Perform update
    await this.profileModel.update(
      {
        ...dto,
        email: profile.email, // prevent email change
        modified_by: dto.modified_by,
        modified_date: new Date(),
      },
      { where: { userId } },
    );

    const updated = await this.profileModel.findByPk(userId);
    return {
      statusCode: HttpStatus.OK,
      error: false,
      message: `Profile updated successfully${isStatusModified ? ` and status changed to ${dto.status ? 'Active' : 'Inactive'}` : ''}`,
      data: updated,
    };
  } catch (error) {
    console.error('Update error:', error);
    return {
      statusCode: HttpStatus.INTERNAL_SERVER_ERROR,
      error: true,
      message: 'Failed to update profile',
    };
  }
}


  // // 🚦 Toggle user status
  // async toggleStatus(userId: string, status: boolean, modifiedBy: string) {
  //   try {
  //     const profile = await this.profileModel.findByPk(userId);
  //     if (!profile) {
  //       return {
  //         statusCode: HttpStatus.NOT_FOUND,
  //         error: true,
  //         message: 'Profile not found',
  //       };
  //     }

  //     if (profile.status === status) {
  //       return {
  //         statusCode: HttpStatus.BAD_REQUEST,
  //         error: true,
  //         message: `User is already ${status ? 'active' : 'inactive'}`,
  //       };
  //     }

  //     await this.profileModel.update(
  //       { status, modified_by: modifiedBy, modified_date: new Date() },
  //       { where: { userId } },
  //     );

  //     return {
  //       statusCode: HttpStatus.OK,
  //       error: false,
  //       message: `User ${status ? 'activated' : 'deactivated'} successfully`,
  //     };
  //   } catch (error) {
  //     return {
  //       statusCode: HttpStatus.INTERNAL_SERVER_ERROR,
  //       error: true,
  //       message: 'Failed to update user status',
  //     };
  //   }
  // }
}
