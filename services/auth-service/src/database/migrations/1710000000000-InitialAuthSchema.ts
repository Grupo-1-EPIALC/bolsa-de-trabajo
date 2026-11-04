import { MigrationInterface, QueryRunner } from 'typeorm';

export class InitialAuthSchema1710000000000 implements MigrationInterface {
  name = 'InitialAuthSchema1710000000000';

  async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`
      CREATE TABLE auth.users (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        email varchar(320) NOT NULL,
        password_hash text NOT NULL,
        role varchar(20) NOT NULL CHECK (role IN ('student', 'company', 'admin')),
        pending_email varchar(320),
        email_verified_at timestamptz,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
      )
    `);
    await queryRunner.query(
      'CREATE UNIQUE INDEX users_email_lower_unique ON auth.users (lower(email))',
    );
    await queryRunner.query(`
      CREATE TABLE auth.companies (
        user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
        legal_name varchar(200) NOT NULL,
        cuit varchar(11) NOT NULL UNIQUE,
        activity varchar(160) NOT NULL
      )
    `);
    await queryRunner.query(`
      CREATE TABLE auth.refresh_sessions (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
        token_hash char(64) NOT NULL UNIQUE,
        expires_at timestamptz NOT NULL,
        revoked_at timestamptz,
        created_at timestamptz NOT NULL DEFAULT now()
      )
    `);
    await queryRunner.query(`
      CREATE TABLE auth.action_tokens (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
        token_hash char(64) NOT NULL UNIQUE,
        purpose varchar(24) NOT NULL CHECK (purpose IN ('password_reset', 'email_change')),
        target_email varchar(320),
        expires_at timestamptz NOT NULL,
        consumed_at timestamptz,
        created_at timestamptz NOT NULL DEFAULT now()
      )
    `);
    await queryRunner.query(
      'CREATE INDEX refresh_sessions_user_active ON auth.refresh_sessions (user_id) WHERE revoked_at IS NULL',
    );
    await queryRunner.query(
      'CREATE INDEX action_tokens_user_purpose ON auth.action_tokens (user_id, purpose) WHERE consumed_at IS NULL',
    );
  }

  async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query('DROP TABLE auth.action_tokens');
    await queryRunner.query('DROP TABLE auth.refresh_sessions');
    await queryRunner.query('DROP TABLE auth.companies');
    await queryRunner.query('DROP TABLE auth.users');
  }
}
