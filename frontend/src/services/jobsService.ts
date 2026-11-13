// jobs-service · ofertas y búsquedas de empresas (contracts/jobs.md, parte A).
import { apiFetch } from './api';
import type {
  Applicant,
  ApplicantList,
  JobCreateInput,
  JobList,
  JobOpportunity,
  JobStatusFilter,
  JobUpdateInput,
  MyApplicationList,
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

  /** POST /jobs/{id}/applications · postula al estudiante (idempotente). 409 PROFILE_REQUIRED sin perfil. */
  apply(jobId: string): Promise<Applicant> {
    return apiFetch<Applicant>(`/jobs/${encodeURIComponent(jobId)}/applications`, {
      method: 'POST',
    });
  },

  /** DELETE /jobs/{id}/applications/me · retira la postulación (idempotente). */
  withdraw(jobId: string): Promise<void> {
    return apiFetch<void>(`/jobs/${encodeURIComponent(jobId)}/applications/me`, {
      method: 'DELETE',
    });
  },

  /** GET /jobs/applications/me · ofertas a las que se postuló el estudiante. */
  myApplications(): Promise<MyApplicationList> {
    return apiFetch<MyApplicationList>('/jobs/applications/me');
  },

  /** GET /jobs/{id}/applications · postulados con su contacto (sólo la empresa dueña). */
  applicants(jobId: string): Promise<ApplicantList> {
    return apiFetch<ApplicantList>(`/jobs/${encodeURIComponent(jobId)}/applications`);
  },

  /** PATCH /jobs/{id} con {"status":"active"} · reabre una búsqueda cerrada. */
  reopen(jobId: string): Promise<JobOpportunity> {
    return this.update(jobId, { status: 'active' });
  },
};
