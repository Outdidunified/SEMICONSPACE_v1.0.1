import {
  Table,
  Column,
  Model,
  DataType,
  PrimaryKey,
} from 'sequelize-typescript';

@Table({ tableName: 'orders' }) // ✅ MUST match actual table
export class ManagerOrder extends Model<ManagerOrder> {
  @PrimaryKey
  @Column({ type: DataType.UUID })
  orderId: string;

  @Column({ type: DataType.UUID })
  userId: string;

  @Column({ type: DataType.JSONB })
  items: any;

  @Column(DataType.DOUBLE)
  total: number;

  @Column
  status: string;

  @Column({ type: DataType.JSONB })
  deliveryAddress: any;

  @Column
  razorpayOrderId: string;

  @Column
  razorpayPaymentId: string;

  @Column
  createdAt: Date;

  @Column
  updatedAt: Date;
}
