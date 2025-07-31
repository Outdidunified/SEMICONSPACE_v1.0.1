import { Controller, Get, Post, Put, Body, Param, ParseUUIDPipe } from '@nestjs/common';
import { ManagerOrderService } from './managerorder.service';
import { UpdateManagerOrderDto } from './dto/update-managerorder.dto';

@Controller('order/admin') // Main prefix changed to 'order'
export class ManagerOrderController {
  constructor(private readonly orderService: ManagerOrderService) {}

  @Get('manager') // GET /order/manager
  getAllOrders() {
    return this.orderService.findAll();
  }

  @Post('view') // POST /order/view
  getOrderById(@Body('orderId') orderId: string) {
    return this.orderService.findOne(orderId);
  }

  @Put('update') // PUT /order/update
  updateOrder(@Body() dto: UpdateManagerOrderDto) {
    return this.orderService.update(dto.orderId, dto);
  }

  @Post('by-user') // POST /order/by-user
  getOrdersByUserId(@Body('userId') userId: string) {
    return this.orderService.findByUserId(userId);
  }
}
