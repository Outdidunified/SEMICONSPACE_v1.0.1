// cart.controller.ts
import {
  Controller,
  Post,
  Body,
  Get,
  Param,
  Delete,
  UseInterceptors,
  ClassSerializerInterceptor,
  ValidationPipe,
  UsePipes,
} from '@nestjs/common';
import { CartService } from './cart.service';
import { IsString, IsNotEmpty, IsNumber, Min } from 'class-validator';
import { Type } from 'class-transformer';
import { IsInt, NotEquals } from 'class-validator';

class AddToCartDto {
  @IsString()
  @IsNotEmpty()
  userId: string;

  @IsNumber()
  @Min(1)
  @Type(() => Number)
  productId: number;

 @IsInt({ message: 'quantity must be an integer' })
  @Min(1, { message: 'quantity must be at least 1' }) // 👈 This ensures no -1 or 0
  @Type(() => Number)
  quantity: number;
}

@Controller('cart')
@UseInterceptors(ClassSerializerInterceptor)
export class CartController {
  constructor(private readonly cartService: CartService) {}

  @Post('add')
  @UsePipes(new ValidationPipe({ transform: true }))
  async addToCart(@Body() body: AddToCartDto) {
    return this.cartService.handleAddToCart(body);
  }

  @Get('getallcartitems/:userId')
  async getCartItemsByUserId(@Param('userId') userId: string) {
    return this.cartService.handleGetCartItems(userId);
  }

  @Delete('removecartitem/:userId/:productId')
  async removeFromCart(
    @Param('userId') userId: string,
    @Param('productId') productIdParam: string
  ) {
    return this.cartService.handleRemoveFromCart(userId, productIdParam);
  }
}
