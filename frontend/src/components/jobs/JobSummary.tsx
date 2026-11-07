import React from 'react';
import { jobFacts, salaryLabel } from '../../jobs/format';
import { JOB_STATUS, labelOf } from '../../profile/labels';
import type { JobOpportunity } from '../../types/jobs';

interface JobSummaryProps {
  job: JobOpportunity;
  onOpen: () => void;
  /** Mostrar la empresa (listado público) o el estado (búsquedas propias). */
  showCompany?: boolean;
  actions?: React.ReactNode;
}

/** Tarjeta corta de una oferta en un listado. */
export const JobSummary: React.FC<JobSummaryProps> = ({ job, onOpen, showCompany, actions }) => (
  <article className="card card-elevated">
    <div className="card-body p-4 d-flex flex-wrap justify-content-between gap-3">
      <div className="flex-grow-1" style={{ minWidth: '16rem' }}>
        <h3 className="h5 fw-bold mb-1">
          <button type="button" className="btn btn-link p-0 text-start fw-bold" onClick={onOpen}>
            {job.title}
          </button>
        </h3>
        {showCompany && <p className="mb-1 fw-semibold">{job.company_snapshot.name}</p>}
        <p className="small mb-1">{jobFacts(job).join(' · ')}</p>
        <p className="small mb-0">
          <i className="bi bi-cash-coin me-1" aria-hidden="true" />
          {salaryLabel(job.work_conditions?.salary)}
          <span className="ms-3">
            <i className="bi bi-people me-1" aria-hidden="true" />
            {job.vacancies} vacante{job.vacancies === 1 ? '' : 's'}
          </span>
        </p>
      </div>
      <div className="d-flex flex-column align-items-end gap-2">
        {!showCompany && (
          <span
            className={`badge rounded-pill ${job.status === 'active' ? 'text-bg-success' : 'text-bg-secondary'}`}
          >
            {labelOf(JOB_STATUS, job.status)}
          </span>
        )}
        {actions && <div className="d-flex flex-wrap justify-content-end gap-2">{actions}</div>}
      </div>
    </div>
  </article>
);
