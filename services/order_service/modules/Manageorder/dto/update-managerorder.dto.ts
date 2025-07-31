// dto/update-managerorder.dto.ts
import { IsString, IsOptional } from 'class-validator';

export class UpdateManagerOrderDto {
  @IsString()
  orderId: string;

  @IsOptional()
  @IsString()
  status?: string;

  @IsOptional()
  @IsString()
  deliveryAddress?: string;

  @IsOptional()
  totalAmount?: number;
}
