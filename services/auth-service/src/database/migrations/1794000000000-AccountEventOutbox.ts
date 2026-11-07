import { MigrationInterface, QueryRunner } from 'typeorm';

/**
 * Outbox de eventos de cuenta: una fila por evento y suscriptor, escrita en la misma
 * transacción que el cambio de la cuenta. El despachador la entrega con reintentos
 * hasta que el suscriptor responde 2xx (contracts/account_events.md §1).
 *
 * `id` es una identidad creciente: ordena las entregas de un mismo usuario y suscriptor.
 */
export class AccountEventOutbox1794000000000 implements MigrationInterface {
  name = 'AccountEventOutbox1794000000000';

  async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`
      CREATE TABLE auth.account_event_deliveries (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        event_id uuid NOT NULL,
        event_type varchar(64) NOT NULL,
        user_id uuid NOT NULL,
        subscriber varchar(500) NOT NULL,
        payload jsonb NOT NULL,
        attempts integer NOT NULL DEFAULT 0,
        next_attempt_at timestamptz NOT NULL DEFAULT now(),
        last_error text,
        delivered_at timestamptz,
        created_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT account_event_deliveries_event_subscriber_unique UNIQUE (event_id, subscriber)
      )
    `);
    await queryRunner.query(`
      CREATE INDEX account_event_deliveries_pending_idx
        ON auth.account_event_deliveries (next_attempt_at)
        WHERE delivered_at IS NULL
    `);
    await queryRunner.query(`
      CREATE INDEX account_event_deliveries_order_idx
        ON auth.account_event_deliveries (subscriber, user_id, id)
        WHERE delivered_at IS NULL
    `);
  }

  async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query('DROP TABLE IF EXISTS auth.account_event_deliveries');
  }
}
