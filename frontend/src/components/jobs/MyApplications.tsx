import React, { useCallback, useEffect, useState } from 'react';
import { jobsService } from '../../services/jobsService';
import { ApiError, errorMessage } from '../../services/api';
import { applicationErrorMessage, applicationState } from '../../jobs/applications';
import { dateLabel } from '../../jobs/format';
import { CompanyPublicProfileModal } from '../company/CompanyPublicProfileModal';
import { JobDetail } from './JobDetail';
import { ApplyButton } from './ApplyButton';
import { useApplications } from './useApplications';
import type { JobOpportunity, MyApplication } from '../../types/jobs';

interface MyApplicationsProps {
  onBrowseJobs: () => void;
}

/** "Mis postulaciones" del estudiante (GET /jobs/applications/me, contracts/jobs.md A §12). */
export const MyApplications: React.FC<MyApplicationsProps> = ({ onBrowseJobs }) => {
  const [items, setItems] = useState<MyApplication[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<JobOpportunity | null>(null);
  const [company, setCompany] = useState<{ id: string; name: string } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [itemErrors, setItemErrors] = useState<Record<string, string>>({});
  const applications = useApplications();

  const load = useCallback(async () => {
    setError(null);
    try {
      setItems((await jobsService.myApplications()).items);
    } catch (err) {
      setError(errorMessage(err));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const open = async (item: MyApplication) => {
    setItemErrors({});
    try {
      setSelected(await jobsService.get(item.job_id));
    } catch (err) {
      setItemErrors({
        [item.job_id]:
          err instanceof ApiError && err.status === 404
            ? 'Esta oferta ya no está disponible.'
            : errorMessage(err),
      });
      load();
    }
  };

  const withdraw = async (item: MyApplication) => {
    setBusy(item.job_id);
    setItemErrors({});
    try {
      await jobsService.withdraw(item.job_id);
      setItems((current) => (current ?? []).filter((i) => i.job_id !== item.job_id));
    } catch (err) {
      setItemErrors({ [item.job_id]: applicationErrorMessage(err) });
    } finally {
      setBusy(null);
    }
  };

  if (selected) {
    return (
      <JobDetail
        job={selected}
        onBack={() => {
          setSelected(null);
          load(); // pudo retirarse desde el detalle
        }}
        backLabel="Volver a mis postulaciones"
        actions={
          <ApplyButton jobId={selected.id} jobTitle={selected.title} controls={applications} />
        }
      />
    );
  }

  if (error) {
    return (
      <div className="alert alert-danger d-flex justify-content-between align-items-center">
        <span>{error}</span>
        <button type="button" className="btn btn-sm btn-primary btn-pill" onClick={load}>
          Reintentar
        </button>
      </div>
    );
  }

  if (!items) {
    return (
      <div className="text-center py-5">
        <span
          className="spinner-border text-primary"
          role="status"
          aria-label="Cargando tus postulaciones"
        />
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="card card-elevated mx-auto" style={{ maxWidth: '40rem' }}>
        <div className="card-body p-4 text-center">
          <span className="icon-circle mb-3">
            <i className="bi bi-send" aria-hidden="true" />
          </span>
          <h2 className="h5 fw-bold">Todavía no te postulaste a ninguna oferta</h2>
          <p className="small">
            Cuando te postules, vas a ver acá cada oferta y la fecha en que te postulaste.
          </p>
          <button type="button" className="btn btn-primary btn-pill" onClick={onBrowseJobs}>
            Ver ofertas
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="d-grid gap-4">
      <p className="small mb-0">
        Te postulaste a {items.length} oferta{items.length === 1 ? '' : 's'}. Las empresas ven tu
        nombre, email, teléfono y título; si te retirás, dejan de verlos.
      </p>
      {items.map((item) => {
        const state = applicationState(item);
        const itemError = itemErrors[item.job_id];
        return (
          <article key={item.id} className="card card-elevated">
            <div className="card-body p-4 d-flex flex-wrap justify-content-between gap-3">
              <div className="flex-grow-1" style={{ minWidth: '16rem' }}>
                <h3 className="h5 fw-bold mb-1">
                  {state.canOpen ? (
                    <button
                      type="button"
                      className="btn btn-link p-0 text-start fw-bold"
                      onClick={() => open(item)}
                    >
                      {item.job!.title}
                    </button>
                  ) : (
                    (item.job?.title ?? 'Oferta no disponible')
                  )}
                </h3>
                {item.job && (
                  <button
                    type="button"
                    className="btn btn-link p-0 fw-semibold text-decoration-none mb-1"
                    onClick={() =>
                      setCompany({ id: item.job!.company_id, name: item.job!.company_name })
                    }
                    title="Ver perfil de la empresa"
                  >
                    <i className="bi bi-building me-1" aria-hidden="true" />
                    {item.job.company_name}
                  </button>
                )}
                <p className="small mb-0">
                  <i className="bi bi-calendar-check me-1" aria-hidden="true" />
                  Te postulaste el {dateLabel(item.applied_at)}
                </p>
              </div>
              <div className="d-flex flex-column align-items-start align-items-md-end gap-2">
                <span className={`badge rounded-pill ${state.badge}`}>{state.label}</span>
                <div className="d-flex flex-wrap gap-2">
                  {state.canOpen && (
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-primary btn-pill"
                      onClick={() => open(item)}
                    >
                      <i className="bi bi-eye me-1" aria-hidden="true" />
                      Ver oferta
                    </button>
                  )}
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-secondary btn-pill"
                    onClick={() => withdraw(item)}
                    disabled={busy === item.job_id}
                    aria-label={`Retirar la postulación a ${item.job?.title ?? 'esta oferta'}`}
                  >
                    {busy === item.job_id ? (
                      <span className="spinner-border spinner-border-sm me-1" aria-hidden="true" />
                    ) : (
                      <i className="bi bi-x-circle me-1" aria-hidden="true" />
                    )}
                    Retirar postulación
                  </button>
                </div>
                {itemError && (
                  <span className="small text-danger-emphasis" role="alert">
                    {itemError}
                  </span>
                )}
              </div>
            </div>
          </article>
        );
      })}
      {company && (
        <CompanyPublicProfileModal
          companyId={company.id}
          companyNameFallback={company.name}
          onClose={() => setCompany(null)}
        />
      )}
    </div>
  );
};
