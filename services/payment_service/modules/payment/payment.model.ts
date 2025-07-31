import { Table, Model, Column, DataType, CreatedAt } from 'sequelize-typescript';

@Table({ tableName: 'payments', timestamps: true })
export class Payment extends Model {
  @Column({ type: DataType.UUID, primaryKey: true })
  orderId: string;

  @Column({ type: DataType.UUID })
  userId: string;

  @Column(DataType.STRING)
  razorpayOrderId: string;

  @Column(DataType.STRING)
  razorpayPaymentId: string;

  @Column(DataType.STRING)
  status: string;

  @Column(DataType.FLOAT)
  total: number;

  @Column({ type: DataType.JSONB }) // use JSONB or TEXT depending on your DB
items: any[];


  @CreatedAt
  createdAt: Date;
}
