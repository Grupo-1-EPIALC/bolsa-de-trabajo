import { EntityManager } from 'typeorm';
import { UserRole } from '../users/user-role';

export const ACCOUNT_EVENT_OUTBOX = Symbol('ACCOUNT_EVENT_OUTBOX');
export const ACCOUNT_EVENT_SENDER = Symbol('ACCOUNT_EVENT_SENDER');
export const ACCOUNT_EVENT_DELIVERY_STORE = Symbol('ACCOUNT_EVENT_DELIVERY_STORE');

export type AccountEventType = 'account.updated' | 'account.deleted';

/**
 * Evento que auth-service avisa a los demás servicios cuando cambia una cuenta.
 * profile-service y jobs-service lo usan para ocultar al borrado del matching,
 * de los listados y de las búsquedas. No lleva datos sensibles.
 */
export interface AccountEvent {
  /** Igual en todos los reintentos y suscriptores: sirve para deduplicar y rastrear. */
  event_id: string;
  event: AccountEventType;
  user_id: string;
  role: UserRole;
  deleted: boolean;
  email: string;
  company?: { legal_name: string; cuit: string; activity: string };
  actor_id: string;
  occurred_at: string;
}

/**
 * Outbox transaccional: el evento se guarda en la misma transacción que el cambio de la
 * cuenta, así no puede quedar un borrado confirmado sin su aviso pendiente.
 */
export interface AccountEventOutbox {
  /** Guarda una entrega pendiente por suscriptor dentro de la transacción `manager`. */
  enqueue(manager: EntityManager, event: AccountEvent): Promise<void>;
  /** Llamar después del commit: intenta entregar ya, sin esperar al próximo ciclo. */
  afterCommit(): void;
}

/** Envía un evento a un suscriptor. Rechaza (throw) si no respondió 2xx. */
export interface AccountEventSender {
  send(subscriber: string, event: AccountEvent): Promise<void>;
}

export interface PendingDelivery {
  id: string;
  subscriber: string;
  payload: AccountEvent;
  /** Intentos hechos antes de este. */
  attempts: number;
}

/** Persistencia de las entregas pendientes (tabla `auth.account_event_deliveries`). */
export interface DeliveryStore {
  /**
   * Reserva hasta `limit` entregas vencidas por `leaseMs` y las devuelve. Sólo la más
   * vieja pendiente de cada (suscriptor, usuario): los eventos de una cuenta llegan en orden.
   */
  claimDue(limit: number, leaseMs: number): Promise<PendingDelivery[]>;
  markDelivered(id: string): Promise<void>;
  markFailed(id: string, error: string, nextAttemptAt: Date): Promise<void>;
}
