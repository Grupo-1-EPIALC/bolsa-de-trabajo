import React from 'react';
import { dateLabel, jobFacts, salaryLabel } from '../../jobs/format';
import {
  AVAILABILITY_START,
  CONTRACT_DURATION,
  EDUCATION_LEVEL,
  EDUCATION_STATUS,
  EMPLOYMENT_TYPE,
  JOB_STATUS,
  REQUIREMENT_KIND,
  SHIFT,
  WORK_SCHEDULE,
  labelOf,
} from '../../profile/labels';
import type { Options } from '../../profile/labels';
import type { JobOpportunity, RequirementKind } from '../../types/jobs';

const KIND_CLASS: Record<RequirementKind, string> = {
  required: 'text-bg-primary',
  desired: 'text-bg-light border',
  excluding: 'text-bg-danger',
};

const list = (options: Options, values: string[] | undefined) =>
  (values ?? []).map((v) => labelOf(options, v)).join(', ');

const Row: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) =>
  children ? (
    <div className="col-sm-6">
      <dt className="small text-body-secondary fw-normal">{label}</dt>
      <dd className="mb-0">{children}</dd>
    </div>
  ) : null;

interface JobDetailProps {
  job: JobOpportunity;
  /** Botones de la empresa dueña (editar, cerrar, candidatos) o vacío para el estudiante. */
  actions?: React.ReactNode;
  onBack: () => void;
  backLabel?: string;
}

/** Detalle completo de una oferta (contracts/jobs_frontend.md §6 y §7). */
export const JobDetail: React.FC<JobDetailProps> = ({
  job,
  actions,
  onBack,
  backLabel = 'Volver',
}) => {
  const wc = job.work_conditions;
  const req = job.requirements;
  const hours = wc?.weekly_hours ? `${wc.weekly_hours.min}–${wc.weekly_hours.max} hs/semana` : '';
  return (
    <article className="card card-elevated">
      <div className="card-body p-4 p-md-5">
        <button type="button" className="btn btn-link btn-sm px-0 mb-3" onClick={onBack}>
          <i className="bi bi-arrow-left me-1" aria-hidden="true" />
          {backLabel}
        </button>
        <div className="d-flex flex-wrap justify-content-between align-items-start gap-3 mb-3">
          <div>
            <h2 className="section-title h3 mb-1">{job.title}</h2>
            <p className="mb-1">
              <strong>{job.company_snapshot.name}</strong>
              {job.company_snapshot.industry && ` · ${job.company_snapshot.industry}`}
            </p>
            <p className="small mb-0">{jobFacts(job).join(' · ')}</p>
          </div>
          <div className="text-md-end">
            <span
              className={`badge rounded-pill ${job.status === 'active' ? 'text-bg-success' : 'text-bg-secondary'}`}
            >
              {labelOf(JOB_STATUS, job.status)}
            </span>
            <p className="fw-semibold mb-0 mt-2">{salaryLabel(wc?.salary)}</p>
          </div>
        </div>
        {actions && <div className="d-flex flex-wrap gap-2 mb-4">{actions}</div>}

        <p style={{ whiteSpace: 'pre-line' }}>{job.description}</p>
        {job.responsibilities.length > 0 && (
          <>
            <h3 className="h6 fw-bold">Responsabilidades</h3>
            <ul>
              {job.responsibilities.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          </>
        )}

        <h3 className="h6 fw-bold mt-4">Requisitos</h3>
        <div className="d-flex flex-wrap gap-2 mb-3">
          {req.skills.map((s) => (
            <span key={s.name} className={`badge ${KIND_CLASS[s.kind]}`}>
              {s.name} · nivel {s.level} · {labelOf(REQUIREMENT_KIND, s.kind)}
            </span>
          ))}
        </div>
        <dl className="row g-3 mb-0">
          <Row label="Experiencia">
            {req.experience &&
              `${req.experience.min_years} año${req.experience.min_years === 1 ? '' : 's'}${
                req.experience.area ? ` en ${req.experience.area}` : ''
              } (${labelOf(REQUIREMENT_KIND, req.experience.kind).toLowerCase()})`}
          </Row>
          <Row label="Idiomas">
            {req.languages
              .map(
                (l) => `${l.name} ${l.level} (${labelOf(REQUIREMENT_KIND, l.kind).toLowerCase()})`,
              )
              .join(', ')}
          </Row>
          <Row label="Formación">
            {req.education
              .map(
                (e) =>
                  `${labelOf(EDUCATION_LEVEL, e.level)} ${labelOf(EDUCATION_STATUS, e.status).toLowerCase()}${
                    e.field ? ` en ${e.field}` : ''
                  }`,
              )
              .join(', ')}
          </Row>
          <Row label="Certificaciones">{req.certifications.map((c) => c.name).join(', ')}</Row>
        </dl>

        <h3 className="h6 fw-bold mt-4">Condiciones</h3>
        <dl className="row g-3 mb-0">
          <Row label="Jornada">{list(WORK_SCHEDULE, wc?.work_schedule)}</Row>
          <Row label="Horas">{hours}</Row>
          <Row label="Contratación">{list(EMPLOYMENT_TYPE, wc?.employment_type)}</Row>
          <Row label="Duración">{list(CONTRACT_DURATION, wc?.contract_duration)}</Row>
          <Row label="Turnos">{list(SHIFT, wc?.shifts)}</Row>
          <Row label="Inicio">
            {wc?.availability_start && labelOf(AVAILABILITY_START, wc.availability_start)}
          </Row>
          <Row label="Días presenciales">
            {typeof wc?.hybrid_onsite_days === 'number' && `${wc.hybrid_onsite_days} por semana`}
          </Row>
          <Row label="Vacantes">{String(job.vacancies)}</Row>
        </dl>

        {job.benefits.length > 0 && (
          <>
            <h3 className="h6 fw-bold mt-4">Beneficios</h3>
            <div className="d-flex flex-wrap gap-1">
              {job.benefits.map((b) => (
                <span key={b} className="badge bg-soft text-magenta border border-primary-subtle">
                  {b}
                </span>
              ))}
            </div>
          </>
        )}

        <p className="small text-body-secondary mt-4 mb-0">
          {job.published_at && `Publicada el ${dateLabel(job.published_at)}`}
          {job.expires_at && ` · Cierra el ${dateLabel(job.expires_at)}`}
        </p>
      </div>
    </article>
  );
};
