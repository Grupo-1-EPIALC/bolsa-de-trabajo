import { MigrationInterface, QueryRunner } from 'typeorm';

/**
 * Versión de los access tokens de cada cuenta. Viaja en el JWT (`tv`) y auth-service la
 * compara en cada request: al subirla (reset, borrado, cambio de clave), los access
 * tokens ya emitidos dejan de valer al instante, sin esperar a que venzan.
 */
export class TokenVersion1794000000001 implements MigrationInterface {
  name = 'TokenVersion1794000000001';

  async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(
      'ALTER TABLE auth.users ADD COLUMN token_version integer NOT NULL DEFAULT 0',
    );
  }

  async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query('ALTER TABLE auth.users DROP COLUMN token_version');
  }
}
