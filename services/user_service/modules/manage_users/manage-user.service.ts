import { Injectable, HttpException, HttpStatus } from "@nestjs/common";
import { InjectModel } from "@nestjs/sequelize";
import { ManageUser } from "./manage-user.model";
import { Profile } from "../../models/profile.model";
import { CreateManageUserDto } from "./dto/create-manage-user.dto";
import { UpdateManageUserDto } from "./dto/update-manage-user.dto";
import { ProducerService } from "../../kafka/producer.service";
import { Op } from "sequelize";

@Injectable()
export class ManageUserService {
  constructor(
    @InjectModel(ManageUser)
    private readonly userModel: typeof ManageUser,
    @InjectModel(Profile)
    private readonly profileModel: typeof Profile,
    private readonly producerService: ProducerService
  ) {}

  // ✅ Shared validation for email & phone uniqueness
  private async validateUniqueEmailPhone(
    email: string,
    phone: string,
    excludeUserId?: string
  ) {
    const where: any = {
      [Op.or]: [{ email }, { phone }],
    };
    if (excludeUserId) {
      where.userId = { [Op.ne]: excludeUserId };
    }

    const existingUser = await this.userModel.findOne({ where });
    if (existingUser) {
      if (existingUser.email === email) {
        return "Email already exists";
      }
      if (existingUser.phone === phone) {
        return "Phone number already exists";
      }
    }
    return null;
  }

  // ✅ Create user in users table and emit Kafka
async create(dto: CreateManageUserDto) {
  try {
    // Validate email and phone uniqueness
    const errorMsg = await this.validateUniqueEmailPhone(dto.email, dto.phone);
    if (errorMsg) {
      return {
        statusCode: HttpStatus.CONFLICT,
        error: true,
        message: errorMsg,
      };
    }

    // Prepare new user data
    const newUserData = {
      first_name: dto.first_name,
      last_name: dto.last_name,
      email: dto.email,
      phone: dto.phone,
      password: dto.password,
      role: dto.role,
      role_id: dto.role_id,
      created_by: dto.created_by,
      created_at: new Date(), // creation timestamp
      modified_date: null, // explicitly set to null at creation
    };

    const new_user = await this.userModel.create(newUserData);

    // Produce Kafka (or other message bus) event
    await this.producerService.produceEvent('user.created', {
      userId: new_user.userId,
      first_name: new_user.first_name,
      last_name: new_user.last_name,
      email: new_user.email,
      password:new_user.password,
      phone: new_user.phone,
      role: new_user.role,
      role_id: new_user.role_id,
      created_at: new_user.created_at?.toISOString(),
      created_by: new_user.created_by,
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
      const allProfiles = await this.profileModel.findAll({
        order: [["created_at", "DESC"]],
      });
      return {
        statusCode: HttpStatus.OK,
        error: false,
        message: "Profiles fetched successfully",
        data: allProfiles,
      };
    } catch (error) {
      return {
        statusCode: HttpStatus.INTERNAL_SERVER_ERROR,
        error: true,
        message: "Failed to fetch profiles",
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
          message: "Profile not found",
        };
      }
      return {
        statusCode: HttpStatus.OK,
        error: false,
        message: "Profile fetched successfully",
        data: profile,
      };
    } catch (error) {
      return {
        statusCode: HttpStatus.INTERNAL_SERVER_ERROR,
        error: true,
        message: "Failed to fetch profile",
      };
    }
  }

  // 📦 Add to manage-user.service.ts

  async getUserStats() {
    try {
      const total = await this.profileModel.count();
      const active = await this.profileModel.count({ where: { status: true } });
      const inactive = await this.profileModel.count({
        where: { status: false },
      });

      return {
        statusCode: HttpStatus.OK,
        error: false,
        message: "User stats fetched successfully",
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
        message: "Failed to fetch user stats",
      };
    }
  }
// ✏️ Update user
async update(
  userId: string,
  dto: UpdateManageUserDto & { modified_by: string }
) {
  try {
    const profile = await this.profileModel.findByPk(userId);
    if (!profile) {
      return {
        statusCode: HttpStatus.NOT_FOUND,
        error: true,
        message: "Profile not found",
      };
    }

    // 🚫 Email immutability check
    if (dto.email && dto.email !== profile.email) {
      return {
        statusCode: HttpStatus.BAD_REQUEST,
        error: true,
        message: "Email cannot be updated",
      };
    }

    let phoneChanged = false;
    let passwordChanged = false;

    // 📞 Phone uniqueness check if updated
    if (dto.phone && dto.phone !== profile.phone) {
      const existingPhone = await this.profileModel.findOne({
        where: {
          phone: dto.phone,
          userId: { [Op.ne]: userId }, // Exclude current user
        },
      });

      if (existingPhone) {
        return {
          statusCode: HttpStatus.CONFLICT,
          error: true,
          message: "Phone number already in use",
        };
      }

      phoneChanged = true;
    }

    // 🔑 Password change detection
    if (dto.password && dto.password !== profile.password) {
      passwordChanged = true;
    }

    // 📝 Detect general changes
    const isModified = [
      "first_name",
      "last_name",
      "phone",
      "password",
      "role",
      "role_id",
    ].some((key) => dto[key] !== undefined && dto[key] !== profile[key]);

    // 🔄 Detect status change
    const isStatusModified =
      typeof dto.status === "boolean" && dto.status !== profile.status;

    if (!isModified && !isStatusModified) {
      return {
        statusCode: HttpStatus.BAD_REQUEST,
        error: true,
        message: "No changes detected",
      };
    }

    // ✅ Perform update
    await this.profileModel.update(
      {
        ...dto,
        email: profile.email, // Keep original email
        modified_by: dto.modified_by,
        modified_date: new Date(),
      },
      { where: { userId } }
    );

    const updated = await this.profileModel.findByPk(userId);

    // 📢 Produce Kafka events
    if (isStatusModified) {
      await this.producerService.produceEvent("user.status.updated", {
        userId: updated.userId,
        email: updated.email,
        oldStatus: profile.status,
        newStatus: updated.status,
        modifiedBy: dto.modified_by,
        modifiedDate: updated.modified_date,
      });
    }

    if (phoneChanged) {
      await this.producerService.produceEvent("user.phone.updated", {
        userId: updated.userId,
        email: updated.email,
        oldPhone: profile.phone,
        newPhone: updated.phone,
        modifiedBy: dto.modified_by,
        modifiedDate: updated.modified_date,
      });
    }

    if (passwordChanged) {
      await this.producerService.produceEvent("user.password.updated", {
        userId: updated.userId,
        email: updated.email,
        modifiedBy: dto.modified_by,
        modifiedDate: updated.modified_date,
      });
    }

    return {
      statusCode: HttpStatus.OK,
      error: false,
      message: `Profile updated successfully${
        isStatusModified
          ? ` and status changed to ${dto.status ? "Active" : "Inactive"}`
          : ""
      }${phoneChanged ? " and phone number updated" : ""}${
        passwordChanged ? " and password updated" : ""
      }`,
      data: updated,
    };
  } catch (error) {
    console.error("Update error:", error);
    return {
      statusCode: HttpStatus.INTERNAL_SERVER_ERROR,
      error: true,
      message:
        error.name === "SequelizeUniqueConstraintError"
          ? "Phone number already exists"
          : "Failed to update profile",
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
