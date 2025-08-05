import {
  Table,
  Column,
  Model,
  DataType,
  PrimaryKey,
} from 'sequelize-typescript';
// services/order_service/modules/Manageorder/managerorder.model.ts

@Table({ tableName: 'orders', timestamps: true })
export class ManagerOrder extends Model<ManagerOrder> {
  @PrimaryKey
  @Column({ type: DataType.UUID })
  orderId!: string;

  @Column({ type: DataType.UUID })
  userId!: string;

  @Column({ type: DataType.JSONB })
  items!: any;

  @Column({ type: DataType.DOUBLE })
  total!: number;

  @Column({ type: DataType.STRING, defaultValue: 'pending' })
  status!: string;

  @Column({ type: DataType.JSONB })
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

  // ✅ Updated to match renamed DB columns
  @Column({ type: DataType.DATE, allowNull: true, field: 'confirmedat' })
  confirmedAt!: Date;

  @Column({ type: DataType.DATE, allowNull: true, field: 'shippedat' })
  shippedAt!: Date;

  @Column({ type: DataType.DATE, allowNull: true, field: 'outfordeliveryat' })
  outForDeliveryAt!: Date;

  @Column({ type: DataType.DATE, allowNull: true, field: 'deliveredat' })
  deliveredAt!: Date;

  @Column({ type: DataType.DATE, field: 'createdat' })
  createdAt!: Date;

  @Column({ type: DataType.DATE, field: 'updatedat' })
  updatedAt!: Date;
}
