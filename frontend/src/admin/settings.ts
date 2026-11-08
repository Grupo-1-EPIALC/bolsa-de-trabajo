// Configuración de matching (contracts/matching.md, parte A §4.5): validación y cambios.
import type { RecommendationSettings, RecommendationSettingsUpdate } from '../types/matching';

export interface SettingsForm {
  student_jobs_limit: string;
  company_candidates_limit: string;
}

export type SettingsErrors = Partial<Record<keyof SettingsForm, string>>;

export const settingsToForm = (s: RecommendationSettings): SettingsForm => ({
  student_jobs_limit: String(s.student_jobs_limit),
  company_candidates_limit: String(s.company_candidates_limit),
});

export function validateSettings(
  form: SettingsForm,
  limits: RecommendationSettings['limits'],
): SettingsErrors {
  const errors: SettingsErrors = {};
  for (const key of ['student_jobs_limit', 'company_candidates_limit'] as const) {
    const raw = form[key].trim();
    const value = Number(raw);
    if (!/^\d+$/.test(raw) || value < limits.min || value > limits.max) {
      errors[key] = `Un número entero entre ${limits.min} y ${limits.max}.`;
    }
  }
  return errors;
}

/** Body del PATCH con sólo lo que cambió. `null` si no hay cambios (el back rechaza el vacío). */
export function settingsUpdate(
  form: SettingsForm,
  current: RecommendationSettings,
): RecommendationSettingsUpdate | null {
  const update: RecommendationSettingsUpdate = {};
  const jobs = Number(form.student_jobs_limit);
  const candidates = Number(form.company_candidates_limit);
  if (jobs !== current.student_jobs_limit) update.student_jobs_limit = jobs;
  if (candidates !== current.company_candidates_limit) {
    update.company_candidates_limit = candidates;
  }
  return Object.keys(update).length ? update : null;
}
