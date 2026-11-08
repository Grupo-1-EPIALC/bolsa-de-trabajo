import React, { useCallback, useEffect, useState } from 'react';
import { JobSummary } from './JobSummary';
import { JobDetail } from './JobDetail';
import { JobForm } from './JobForm';
import { JobCandidates } from './JobCandidates';
import { Pagination } from './Pagination';
import { jobsService } from '../../services/jobsService';
import { ApiError, errorMessage } from '../../services/api';
import { JOB_STATUS_FILTER } from '../../profile/labels';
import type { JobList, JobOpportunity, JobStatusFilter } from '../../types/jobs';

type Mode =
  | { kind: 'list' }
  | { kind: 'new' }
  | { kind: 'edit'; job: JobOpportunity }
  | { kind: 'detail'; job: JobOpportunity }
  | { kind: 'candidates'; job: JobOpportunity };

interface CompanySearchesProps {
  /** Abrir directamente el alta (desde el panel). */
  startWithNew?: boolean;
  onNotice: (message: string) => void;
}

/** "Mis búsquedas" (contracts/jobs.md, parte B §11): listar, crear, editar, cerrar y reabrir. */
export const CompanySearches: React.FC<CompanySearchesProps> = ({ startWithNew, onNotice }) => {
  const [mode, setMode] = useState<Mode>(startWithNew ? { kind: 'new' } : { kind: 'list' });
  const [status, setStatus] = useState<JobStatusFilter>('active');
  const [page, setPage] = useState(1);
  const [data, setData] = useState<JobList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const result = await jobsService.mySearches(status, page);
      // Si cerrar/reabrir dejó la página vacía, volver a la anterior.
      if (result.items.length === 0 && page > 1) setPage(page - 1);
      else setData(result);
    } catch (err) {
      setError(errorMessage(err));
    }
  }, [status, page]);

  useEffect(() => {
    if (mode.kind === 'list') load();
  }, [load, mode.kind]);

  const toList = () => setMode({ kind: 'list' });

  /** Cerrar (DELETE) o reabrir (PATCH status=active). Ante un 409 se relee la búsqueda. */
  const toggle = async (job: JobOpportunity) => {
    setBusyId(job.id);
    setError(null);
    try {
      if (job.status === 'active') {
        await jobsService.close(job.id);
        onNotice('Búsqueda cerrada');
      } else {
        await jobsService.reopen(job.id);
        onNotice('Búsqueda reabierta');
      }
      if (mode.kind === 'detail') setMode({ kind: 'detail', job: await jobsService.get(job.id) });
      else load();
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 409
          ? 'La búsqueda cambió mientras la mirabas. Actualizamos los datos: probá de nuevo.'
          : errorMessage(err),
      );
      load();
    } finally {
      setBusyId(null);
    }
  };

  const actions = (job: JobOpportunity, inDetail = false) => (
    <>
      {!inDetail && (
        <button
          type="button"
          className="btn btn-sm btn-outline-primary btn-pill"
          onClick={() => setMode({ kind: 'detail', job })}
        >
          Ver
        </button>
      )}
      <button
        type="button"
        className="btn btn-sm btn-outline-primary btn-pill"
        onClick={() => setMode({ kind: 'edit', job })}
      >
        <i className="bi bi-pencil me-1" aria-hidden="true" />
        Editar
      </button>
      {job.status === 'active' && (
        <button
          type="button"
          className="btn btn-sm btn-primary btn-pill"
          onClick={() => setMode({ kind: 'candidates', job })}
        >
          <i className="bi bi-people me-1" aria-hidden="true" />
          Candidatos
        </button>
      )}
      <button
        type="button"
        className={`btn btn-sm btn-pill ${job.status === 'active' ? 'btn-outline-danger' : 'btn-outline-success'}`}
        onClick={() => toggle(job)}
        disabled={busyId === job.id}
      >
        {busyId === job.id && (
          <span className="spinner-border spinner-border-sm me-1" aria-hidden="true" />
        )}
        {job.status === 'active' ? 'Cerrar' : 'Reabrir'}
      </button>
    </>
  );

  if (mode.kind === 'new' || mode.kind === 'edit') {
    const editing = mode.kind === 'edit' ? mode.job : undefined;
    return (
      <div className="d-grid gap-3">
        <h2 className="section-title h4 mb-0">
          {editing ? `Editar "${editing.title}"` : 'Nueva búsqueda'}
        </h2>
        <JobForm
          key={editing?.id ?? 'new'}
          job={editing}
          onCancel={() => (editing ? setMode({ kind: 'detail', job: editing }) : toList())}
          onSaved={(saved, created) => {
            onNotice(created ? 'Búsqueda creada' : 'Búsqueda actualizada');
            setMode({ kind: 'detail', job: saved });
          }}
        />
      </div>
    );
  }
  if (mode.kind === 'candidates') {
    return (
      <JobCandidates job={mode.job} onBack={() => setMode({ kind: 'detail', job: mode.job })} />
    );
  }
  if (mode.kind === 'detail') {
    return (
      <div className="d-grid gap-3">
        {error && <div className="alert alert-danger mb-0">{error}</div>}
        <JobDetail
          job={mode.job}
          onBack={toList}
          backLabel="Volver a mis búsquedas"
          actions={actions(mode.job, true)}
        />
      </div>
    );
  }

  return (
    <div className="d-grid gap-4">
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-3">
        <ul className="nav nav-pills" role="tablist" aria-label="Estado de las búsquedas">
          {JOB_STATUS_FILTER.map(([value, label]) => (
            <li className="nav-item" key={value} role="presentation">
              <button
                type="button"
                role="tab"
                aria-selected={status === value}
                className={`nav-link ${status === value ? 'active' : ''}`}
                onClick={() => {
                  setStatus(value);
                  setPage(1);
                }}
              >
                {label}
                {status === value && data && (
                  <span className="badge text-bg-light ms-2">{data.total}</span>
                )}
              </button>
            </li>
          ))}
        </ul>
        <button
          type="button"
          className="btn btn-primary btn-pill"
          onClick={() => setMode({ kind: 'new' })}
        >
          <i className="bi bi-plus-lg me-2" aria-hidden="true" />
          Nueva búsqueda
        </button>
      </div>

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
            aria-label="Cargando búsquedas"
          />
        </div>
      )}
      {data && data.items.length === 0 && (
        <div className="card card-elevated">
          <div className="card-body p-4 text-center">
            <p className="mb-3">
              {status === 'active'
                ? 'Todavía no tenés búsquedas activas.'
                : status === 'closed'
                  ? 'No tenés búsquedas cerradas.'
                  : 'Todavía no publicaste búsquedas.'}
            </p>
            <button
              type="button"
              className="btn btn-primary btn-pill"
              onClick={() => setMode({ kind: 'new' })}
            >
              Publicar una búsqueda
            </button>
          </div>
        </div>
      )}
      {data?.items.map((job) => (
        <JobSummary
          key={job.id}
          job={job}
          onOpen={() => setMode({ kind: 'detail', job })}
          actions={actions(job)}
        />
      ))}
      {data && (
        <Pagination
          page={data.page}
          pages={data.pages}
          onPage={setPage}
          label="Páginas de mis búsquedas"
        />
      )}
    </div>
  );
};
