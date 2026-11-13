// Lógica de postulaciones sin React (contracts/jobs.md, parte A §12).
import { ApiError, errorMessage } from '../services/api';
import type { Applicant, MyApplication, MyApplicationList } from '../types/jobs';
import type { CompanyRuleItem } from '../types/matching';

/** Qué ve la empresa cuando el estudiante se postula (se avisa antes del botón). */
export const SHARED_DATA_NOTE = 'La empresa verá tu nombre, email, teléfono y título.';

/** Ids de las ofertas a las que ya se postuló el estudiante. */
export const appliedJobIds = (list: MyApplicationList): Set<string> =>
  new Set(list.items.map((item) => item.job_id));

/** Mensaje en español para un error al postularse o retirarse. */
export function applicationErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.code === 'PROFILE_REQUIRED') {
      return 'Completá tu perfil (nombre y email) antes de postularte.';
    }
    if (err.status === 404) return 'Esta oferta ya no está disponible.';
  }
  return errorMessage(err);
}

/** Postulados indexados por `profile_id`, para marcarlos en el ranking de recomendados. */
export const applicantsByProfile = (applicants: Applicant[]): Map<string, Applicant> =>
  new Map(applicants.map((a) => [a.profile_id, a]));

/** Puesto en el ranking por reglas de cada perfil recomendado. */
export const rankByProfile = (items: CompanyRuleItem[]): Map<string, CompanyRuleItem> =>
  new Map(items.map((item) => [item.candidate.profile_id, item]));

export interface ApplicationState {
  label: string;
  badge: string;
  /** Se puede abrir el detalle: un estudiante sólo ve ofertas activas. */
  canOpen: boolean;
}

/** Estado de una postulación propia según la oferta (`job` es null si la empresa se dio de baja). */
export function applicationState(item: MyApplication): ApplicationState {
  if (!item.job) return { label: 'No disponible', badge: 'text-bg-secondary', canOpen: false };
  if (item.job.status === 'closed') {
    return { label: 'Búsqueda cerrada', badge: 'text-bg-secondary', canOpen: false };
  }
  return { label: 'Búsqueda activa', badge: 'text-bg-success', canOpen: true };
}
