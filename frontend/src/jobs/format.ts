// Cómo se muestran las ofertas (contracts/jobs_frontend.md §7 y §10).
import { SALARY_PERIOD, SENIORITY, WORK_MODALITY, labelOf } from '../profile/labels';
import type { JobLocation, JobOpportunity, JobSalary } from '../types/jobs';

const money = (amount: number, currency: string) =>
  new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(amount);

/**
 * Sueldo para mostrar. `null` = la empresa no lo publica para quien mira (§7): nunca "$ 0".
 * `to_agree` o sin montos = "A convenir".
 */
export function salaryLabel(salary: JobSalary | null | undefined): string {
  if (!salary) return 'Sueldo no publicado';
  const { min, max, to_agree: toAgree } = salary;
  const hasMin = typeof min === 'number';
  const hasMax = typeof max === 'number';
  if (toAgree || (!hasMin && !hasMax)) return 'A convenir';
  const currency = salary.currency ?? 'ARS';
  let amount: string;
  if (hasMin && hasMax && min !== max) amount = `${money(min, currency)} – ${money(max, currency)}`;
  else if (hasMin && hasMax) amount = money(min, currency);
  else if (hasMin) amount = `Desde ${money(min, currency)}`;
  else amount = `Hasta ${money(max as number, currency)}`;
  const period = salary.period ? ` ${labelOf(SALARY_PERIOD, salary.period)}` : '';
  const gross = salary.gross === false ? ' (neto)' : '';
  return `${amount}${period}${gross}`;
}

export function placeLabel(location: Partial<JobLocation> | null | undefined): string {
  return [location?.city, location?.province].filter(Boolean).join(', ');
}

/** Datos cortos de una oferta: área · seniority · lugar · modalidades. */
export function jobFacts(job: JobOpportunity): string[] {
  const modality = (job.work_conditions?.work_modality ?? [])
    .map((m) => labelOf(WORK_MODALITY, m))
    .join(' / ');
  return [job.area, labelOf(SENIORITY, job.seniority), placeLabel(job.location), modality].filter(
    (value): value is string => Boolean(value),
  );
}

/** Fecha corta en es-AR (`5 nov 2026`); vacío si no hay fecha. */
export function dateLabel(iso: string | null | undefined): string {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleDateString('es-AR', { day: 'numeric', month: 'short', year: 'numeric' });
}
