import React, { useCallback, useEffect, useState } from 'react';
import { JobSummary } from './JobSummary';
import { JobDetail } from './JobDetail';
import { Pagination } from './Pagination';
import { TrainingAdvice } from '../matching/TrainingAdvice';
import { jobsService } from '../../services/jobsService';
import { ApiError, errorMessage } from '../../services/api';
import type { JobList, JobOpportunity } from '../../types/jobs';

interface JobBoardProps {
  /** Perfil del estudiante: habilita "¿Cómo mejorar para esta oferta?" en el detalle. */
  profileId?: string;
}

/** "Todas las ofertas" (GET /jobs, sólo activas): listado paginado y detalle. */
export const JobBoard: React.FC<JobBoardProps> = ({ profileId }) => {
  const [page, setPage] = useState(1);
  const [data, setData] = useState<JobList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<JobOpportunity | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setData(await jobsService.list(page));
    } catch (err) {
      setError(errorMessage(err));
    }
  }, [page]);

  useEffect(() => {
    load();
  }, [load]);

  const open = async (job: JobOpportunity) => {
    setError(null);
    try {
      // El listado ya trae la oferta completa; se relee por si cambió o se cerró.
      setSelected(await jobsService.get(job.id));
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 404
          ? 'Esta oferta ya no está disponible.'
          : errorMessage(err),
      );
      load();
    }
  };

  if (selected) {
    return (
      <JobDetail job={selected} onBack={() => setSelected(null)} backLabel="Volver a las ofertas">
        {profileId && <TrainingAdvice profileId={profileId} jobId={selected.id} />}
      </JobDetail>
    );
  }

  return (
    <div className="d-grid gap-4">
      {data && (
        <p className="small mb-0">
          {data.total} oferta{data.total === 1 ? '' : 's'} activa{data.total === 1 ? '' : 's'}. Las
          que más coinciden con tu perfil están en "Ofertas para vos".
        </p>
      )}
      {error && (
        <div className="alert alert-danger d-flex justify-content-between align-items-center mb-0">
          <span>{error}</span>
          <button type="button" className="btn btn-sm btn-primary btn-pill" onClick={load}>
            Reintentar
          </button>
        </div>
      )}
      {!data && !error && (
        <div className="text-center py-5">
          <span
            className="spinner-border text-primary"
            role="status"
            aria-label="Cargando ofertas"
          />
        </div>
      )}
      {data && data.items.length === 0 && (
        <div className="card card-elevated">
          <div className="card-body p-4 text-center">Todavía no hay ofertas publicadas.</div>
        </div>
      )}
      {data?.items.map((job) => (
        <JobSummary key={job.id} job={job} showCompany onOpen={() => open(job)} />
      ))}
      {data && (
        <Pagination
          page={data.page}
          pages={data.pages}
          onPage={setPage}
          label="Páginas de ofertas"
        />
      )}
    </div>
  );
};
