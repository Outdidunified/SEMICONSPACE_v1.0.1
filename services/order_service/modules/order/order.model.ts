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

  @Column(DataType.STRING)
  razorpayOrderId!: string;

  @Column(DataType.STRING)
  razorpayPaymentId!: string;

  // ✅ Add field mappings here
  @Column({ type: DataType.DATE, field: 'confirmedat' }) // or 'confirmed_at' if that's what your DB uses
  confirmedAt!: Date;

  @Column({ type: DataType.DATE, field: 'shippedat' })
  shippedAt!: Date;

  @Column({ type: DataType.DATE, field: 'outfordeliveryat' })
  outForDeliveryAt!: Date;

  @Column({ type: DataType.DATE, field: 'deliveredat' })
  deliveredAt!: Date;

  @Column({ type: DataType.DATE, field: 'createdat' })
  createdAt!: Date;

  @Column({ type: DataType.DATE, field: 'updatedat' })
  updatedAt!: Date;
}
