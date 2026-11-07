import { UserRole } from '../users/user-role';

export const ACCOUNT_EVENT_PUBLISHER = Symbol('ACCOUNT_EVENT_PUBLISHER');

export type AccountEventType = 'account.updated' | 'account.deleted';

/**
 * Evento que auth-service avisa a los demás servicios cuando cambia una cuenta.
 * profile-service y jobs-service lo usan para ocultar al borrado del matching,
 * de los listados y de las búsquedas. No lleva datos sensibles.
 */
export interface AccountEvent {
  event: AccountEventType;
  user_id: string;
  role: UserRole;
  deleted: boolean;
  email: string;
  company?: { legal_name: string; cuit: string; activity: string };
  actor_id: string;
  occurred_at: string;
}

export interface AccountEventPublisher {
  /** Best effort: un suscriptor caído no hace fallar la operación del admin. */
  publish(event: AccountEvent): Promise<void>;
}
