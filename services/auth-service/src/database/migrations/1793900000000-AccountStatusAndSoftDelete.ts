import { MigrationInterface, QueryRunner } from 'typeorm';

/**
 * Estado de la cuenta (activa/suspendida) y soft delete.
 * El email y el CUIT pasan a ser únicos sólo entre cuentas NO borradas, así una cuenta
 * borrada permite una nueva alta con el mismo email o CUIT y la vieja queda para auditoría.
 */
export class AccountStatusAndSoftDelete1793900000000 implements MigrationInterface {
  name = 'AccountStatusAndSoftDelete1793900000000';

  async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`
      ALTER TABLE auth.users
        ADD COLUMN status varchar(20) NOT NULL DEFAULT 'active'
          CHECK (status IN ('active', 'suspended')),
        ADD COLUMN suspended_at timestamptz,
        ADD COLUMN suspension_reason varchar(500),
        ADD COLUMN deleted_at timestamptz
    `);
    await queryRunner.query('DROP INDEX IF EXISTS auth.users_email_lower_unique');
    await queryRunner.query(
      'CREATE UNIQUE INDEX users_email_lower_active_unique ON auth.users (lower(email)) WHERE deleted_at IS NULL',
    );
    await queryRunner.query(
      'CREATE INDEX users_role_status ON auth.users (role, status) WHERE deleted_at IS NULL',
    );

    await queryRunner.query('ALTER TABLE auth.companies ADD COLUMN deleted_at timestamptz');
    await queryRunner.query(
      'ALTER TABLE auth.companies DROP CONSTRAINT IF EXISTS companies_cuit_key',
    );
    await queryRunner.query(
      'CREATE UNIQUE INDEX companies_cuit_active_unique ON auth.companies (cuit) WHERE deleted_at IS NULL',
    );
  }

  async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query('DROP INDEX IF EXISTS auth.companies_cuit_active_unique');
    await queryRunner.query(
      'ALTER TABLE auth.companies ADD CONSTRAINT companies_cuit_key UNIQUE (cuit)',
    );
    await queryRunner.query('ALTER TABLE auth.companies DROP COLUMN deleted_at');
    await queryRunner.query('DROP INDEX IF EXISTS auth.users_role_status');
    await queryRunner.query('DROP INDEX IF EXISTS auth.users_email_lower_active_unique');
    await queryRunner.query(
      'CREATE UNIQUE INDEX users_email_lower_unique ON auth.users (lower(email))',
    );
    await queryRunner.query(`
      ALTER TABLE auth.users
        DROP COLUMN deleted_at,
        DROP COLUMN suspension_reason,
        DROP COLUMN suspended_at,
        DROP COLUMN status
    `);
  }
}
