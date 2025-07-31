

// services/order_service/modules/order/dto/create-order.dto.ts
import { IsArray, IsNumber, IsString, IsUUID } from 'class-validator';

export class CreateOrderDto {
  @IsUUID()
  userId!: string;

  @IsArray()
  items!: Array<{ 
    productId: string; 
    qty: number; 
    price: number;
  }>;

  @IsNumber()
  total!: number;

  @IsString()
  status!: string;
}
