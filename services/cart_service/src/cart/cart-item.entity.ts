// src/cart/cart-item.entity.ts
import { Entity, Column, PrimaryGeneratedColumn, Double } from 'typeorm';

@Entity('cart_items')
export class CartItem {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column()
  userId: string;

  @Column()
  productId: number;

  @Column()
  quantity: number;

  @Column({ nullable: true })
  externalProductId: string;

  @Column({ nullable: true })
  supplier: string;

  @Column({ nullable: true })
  name: string;

  @Column({ nullable: true })
  description: string;

  @Column({ nullable: true })
  manufacturerId: number;

  @Column({ nullable: true })
  manufacturerPartNumber: string;

  @Column({ nullable: true })
  category: string;

  @Column({ type: 'double precision', nullable: true }) // or 'double' for MySQL
  price: number;

  @Column({ nullable: true })
  packageType: string;

  @Column({ nullable: true })
  datasheetUrl: string;

  @Column({ nullable: true })
  imageUrl: string;

  @Column({ type: 'timestamp', nullable: true })
  lastFetchedAt: Date;

  @Column({ nullable: true })
  categoryId: number;

  @Column({ nullable: true })
  createdBy: string;

  @Column({ nullable: true })
  modifiedBy: string;

  @Column({ type: 'timestamp', nullable: true })
  createdDate: Date;

  @Column({ type: 'timestamp', nullable: true })
  modifiedDate: Date;

  @Column({ default: true })
  status: boolean;
}
