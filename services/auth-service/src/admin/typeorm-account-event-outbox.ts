import { Injectable } from '@nestjs/common';
import { DataSource, EntityManager } from 'typeorm';
import { AccountEvent, AccountEventOutbox, DeliveryStore, PendingDelivery } from './account-events';

const TABLE = 'auth.account_event_deliveries';

/** Escribe las entregas pendientes en la transacción del caso de uso. */
export class TypeOrmAccountEventOutbox implements AccountEventOutbox {
  constructor(
    private readonly subscribers: string[],
    private readonly onCommitted: () => void,
  ) {}

  async enqueue(manager: EntityManager, event: AccountEvent): Promise<void> {
    for (const subscriber of this.subscribers) {
      await manager.query(
        `INSERT INTO ${TABLE} (event_id, event_type, user_id, subscriber, payload)
         VALUES ($1, $2, $3, $4, $5::jsonb)`,
        [event.event_id, event.event, event.user_id, subscriber, JSON.stringify(event)],
      );
    }
  }

  afterCommit(): void {
    if (this.subscribers.length) this.onCommitted();
  }
}

interface ClaimedRow {
  id: string;
  subscriber: string;
  payload: AccountEvent | string;
  attempts: number;
}

/**
 * Entregas pendientes en Postgres. `claimDue` usa FOR UPDATE SKIP LOCKED y un lease
 * (corre `next_attempt_at`), así dos réplicas de auth-service no mandan la misma entrega
 * a la vez y una entrega cuyo envío se cortó a mitad de camino vuelve sola a la cola.
 */
@Injectable()
export class TypeOrmDeliveryStore implements DeliveryStore {
  constructor(private readonly dataSource: DataSource) {}

  async claimDue(limit: number, leaseMs: number): Promise<PendingDelivery[]> {
    const rows = (await this.dataSource.query(
      `UPDATE ${TABLE} d
          SET next_attempt_at = now() + make_interval(secs => $2::double precision / 1000)
        WHERE d.id IN (
          SELECT c.id FROM ${TABLE} c
           WHERE c.delivered_at IS NULL
             AND c.next_attempt_at <= now()
             AND NOT EXISTS (
               SELECT 1 FROM ${TABLE} p
                WHERE p.delivered_at IS NULL
                  AND p.subscriber = c.subscriber
                  AND p.user_id = c.user_id
                  AND p.id < c.id)
           ORDER BY c.id
           LIMIT $1
           FOR UPDATE SKIP LOCKED)
      RETURNING d.id::text AS id, d.subscriber, d.payload, d.attempts`,
      [limit, leaseMs],
    )) as unknown;
    // UPDATE ... RETURNING con el driver pg devuelve [filas, cantidad].
    const list = (Array.isArray(rows) && Array.isArray(rows[0]) ? rows[0] : rows) as ClaimedRow[];
    return list
      .map((row) => ({
        id: String(row.id),
        subscriber: row.subscriber,
        payload: (typeof row.payload === 'string'
          ? JSON.parse(row.payload)
          : row.payload) as AccountEvent,
        attempts: Number(row.attempts),
      }))
      .sort((a, b) => Number(a.id) - Number(b.id));
  }

  async markDelivered(id: string): Promise<void> {
    await this.dataSource.query(
      `UPDATE ${TABLE} SET delivered_at = now(), attempts = attempts + 1, last_error = NULL
        WHERE id = $1`,
      [id],
    );
  }

  async markFailed(id: string, error: string, nextAttemptAt: Date): Promise<void> {
    await this.dataSource.query(
      `UPDATE ${TABLE} SET attempts = attempts + 1, last_error = $2, next_attempt_at = $3
        WHERE id = $1`,
      [id, error.slice(0, 1000), nextAttemptAt],
    );
  }
}
