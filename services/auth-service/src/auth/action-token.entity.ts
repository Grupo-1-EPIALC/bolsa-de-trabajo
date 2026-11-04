import { Column, CreateDateColumn, Entity, Index, PrimaryGeneratedColumn } from 'typeorm';

export enum ActionTokenPurpose {
  PASSWORD_RESET = 'password_reset',
  EMAIL_CHANGE = 'email_change',
}

@Entity({ name: 'action_tokens', schema: 'auth' })
@Index('action_tokens_token_hash_unique', ['tokenHash'], { unique: true })
export class ActionToken {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column({ name: 'user_id', type: 'uuid' })
  userId!: string;

  @Column({ name: 'token_hash', type: 'char', length: 64 })
  tokenHash!: string;

  @Column({ type: 'varchar', length: 24 })
  purpose!: ActionTokenPurpose;

  @Column({ name: 'target_email', type: 'varchar', length: 320, nullable: true })
  targetEmail!: string | null;

  @Column({ name: 'expires_at', type: 'timestamptz' })
  expiresAt!: Date;

  @Column({ name: 'consumed_at', type: 'timestamptz', nullable: true })
  consumedAt!: Date | null;

  @CreateDateColumn({ name: 'created_at', type: 'timestamptz' })
  createdAt!: Date;
}
