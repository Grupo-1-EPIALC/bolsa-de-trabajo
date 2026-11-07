import { Column, Entity, JoinColumn, OneToOne, PrimaryColumn } from 'typeorm';
import { User } from './user.entity';

@Entity({ name: 'companies', schema: 'auth' })
export class Company {
  @PrimaryColumn({ name: 'user_id', type: 'uuid' })
  userId!: string;

  @Column({ name: 'legal_name', type: 'varchar', length: 200 })
  legalName!: string;

  /** Único entre empresas no borradas (índice parcial companies_cuit_active_unique). */
  @Column({ type: 'varchar', length: 11 })
  cuit!: string;

  @Column({ type: 'varchar', length: 160 })
  activity!: string;

  /** Copia del borrado lógico de la cuenta, para que el CUIT quede libre para una nueva alta. */
  @Column({ name: 'deleted_at', type: 'timestamptz', nullable: true })
  deletedAt!: Date | null;

  @OneToOne(() => User, (user) => user.company, { onDelete: 'CASCADE' })
  @JoinColumn({ name: 'user_id', referencedColumnName: 'id' })
  user!: User;
}
