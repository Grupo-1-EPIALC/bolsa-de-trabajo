// jobs-service · ofertas y búsquedas de empresas (contracts/jobs.md, parte A).
import { apiFetch } from './api';
import type {
  JobCreateInput,
  JobList,
  JobOpportunity,
  JobStatusFilter,
  JobUpdateInput,
} from '../types/jobs';

export const PAGE_SIZE = 10;

const query = (status: JobStatusFilter, page: number, size: number) =>
  new URLSearchParams({ status, page: String(page), size: String(size) }).toString();

export const jobsService = {
  /** GET /jobs · ofertas activas (estudiantes y empresas sólo ven `active`). */
  list(page = 1, size = PAGE_SIZE): Promise<JobList> {
    return apiFetch<JobList>(`/jobs?${query('active', page, size)}`);
  },

  /** GET /companies/me/searches · búsquedas de la empresa, con el sueldo completo. */
  mySearches(status: JobStatusFilter = 'active', page = 1, size = PAGE_SIZE): Promise<JobList> {
    return apiFetch<JobList>(`/companies/me/searches?${query(status, page, size)}`);
  },

  /** GET /jobs/{id} · una oferta cerrada de otra empresa da 404. */
  get(jobId: string): Promise<JobOpportunity> {
    return apiFetch<JobOpportunity>(`/jobs/${encodeURIComponent(jobId)}`);
  },

  /** POST /jobs · nace `active`; company_id y company_snapshot los pone el servicio. */
  create(input: JobCreateInput): Promise<JobOpportunity> {
    return apiFetch<JobOpportunity>('/jobs', { method: 'POST', body: JSON.stringify(input) });
  },

  /** PATCH /jobs/{id} · cada bloque enviado se reemplaza entero. 409 si otro la editó antes. */
  update(jobId: string, input: JobUpdateInput): Promise<JobOpportunity> {
    return apiFetch<JobOpportunity>(`/jobs/${encodeURIComponent(jobId)}`, {
      method: 'PATCH',
      body: JSON.stringify(input),
    });
  },

  /** DELETE /jobs/{id} · cierra la búsqueda (no la borra). Idempotente. */
  close(jobId: string): Promise<void> {
    return apiFetch<void>(`/jobs/${encodeURIComponent(jobId)}`, { method: 'DELETE' });
  },

  /** PATCH /jobs/{id} con {"status":"active"} · reabre una búsqueda cerrada. */
  reopen(jobId: string): Promise<JobOpportunity> {
    return this.update(jobId, { status: 'active' });
  },
};
