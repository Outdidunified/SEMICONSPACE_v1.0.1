
// src/modules/order/order.model.ts
// services/order_service/modules/order/order.model.ts
import { Column, DataType, Model, Table } from 'sequelize-typescript';

@Table({ tableName: 'orders', timestamps: true })
export class Order extends Model {
  @Column({ type: DataType.UUID, primaryKey: true, defaultValue: DataType.UUIDV4 })
  orderId!: string;

  @Column({ type: DataType.UUID, allowNull: false })
  userId!: string;

  @Column(DataType.JSONB)
  items!: Array<{ productId: string; qty: number; price: number; totalPrice: number }>;

  @Column(DataType.FLOAT)
  total!: number;

  @Column({ type: DataType.STRING, defaultValue: 'pending' })
  status!: string;

  @Column(DataType.JSONB)
  deliveryAddress!: {
    address: string;
    pin: string;
    city: string;
    state: string;
  };

  @Column({ type: DataType.STRING, allowNull: true })
  razorpayOrderId!: string;

  @Column({ type: DataType.STRING, allowNull: true })
  razorpayPaymentId!: string;

  @Column({ type: DataType.DATE })
  createdAt!: Date;

  @Column({ type: DataType.DATE })
  updatedAt!: Date;
}
