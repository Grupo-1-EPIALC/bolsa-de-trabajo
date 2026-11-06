import {
  Column,
  CreateDateColumn,
  DeleteDateColumn,
  Entity,
  OneToOne,
  PrimaryGeneratedColumn,
  UpdateDateColumn,
} from 'typeorm';
import { AccountStatus } from './account-status';
import { Company } from './company.entity';
import { UserRole } from './user-role';

@Entity({ name: 'users', schema: 'auth' })
export class User {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column({ type: 'varchar', length: 320 })
  email!: string;

  @Column({ name: 'password_hash', type: 'text', select: false })
  passwordHash!: string;

  @Column({ type: 'varchar', length: 20 })
  role!: UserRole;

  @Column({ name: 'pending_email', type: 'varchar', length: 320, nullable: true })
  pendingEmail!: string | null;

  @Column({ name: 'email_verified_at', type: 'timestamptz', nullable: true })
  emailVerifiedAt!: Date | null;

  @CreateDateColumn({ name: 'created_at', type: 'timestamptz' })
  createdAt!: Date;

  @UpdateDateColumn({ name: 'updated_at', type: 'timestamptz' })
  updatedAt!: Date;

  @Column({ type: 'varchar', length: 20, default: AccountStatus.ACTIVE })
  status!: AccountStatus;

  @Column({ name: 'suspended_at', type: 'timestamptz', nullable: true })
  suspendedAt!: Date | null;

  @Column({ name: 'suspension_reason', type: 'varchar', length: 500, nullable: true })
  suspensionReason!: string | null;

  /**
   * Borrado lógico: TypeORM excluye estas filas de find() y de los query builders
   * (salvo withDeleted()), así login, refresh y registro ignoran las cuentas borradas.
   */
  @DeleteDateColumn({ name: 'deleted_at', type: 'timestamptz', nullable: true })
  deletedAt!: Date | null;

  @OneToOne(() => Company, (company) => company.user)
  company?: Company;
}
