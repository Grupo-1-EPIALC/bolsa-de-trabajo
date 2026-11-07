import React, { useEffect, useState } from 'react';
import { CompanyLogo } from './CompanyLogo';
import { CompletionCard } from '../profile/CompletionCard';
import { jobsService } from '../../services/jobsService';
import { errorMessage } from '../../services/api';
import { COMPANY_SIZE, labelOf } from '../../profile/labels';
import { jobFacts } from '../../jobs/format';
import type { CompanyProfile, CompanyStep } from '../../types/company';
import type { JobList } from '../../types/jobs';

interface CompanyDashboardProps {
  profile: CompanyProfile;
  onEdit: (step: CompanyStep) => void;
  onSearches: () => void;
  onNewSearch: () => void;
}

/** Panel de la empresa: su perfil, la completitud y sus búsquedas activas (jobs-service). */
export const CompanyDashboard: React.FC<CompanyDashboardProps> = ({
  profile,
  onEdit,
  onSearches,
  onNewSearch,
}) => {
  const [searches, setSearches] = useState<JobList | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);

  useEffect(() => {
    jobsService
      .mySearches('active', 1, 5)
      .then(setSearches)
      .catch((err) => setSearchError(errorMessage(err)));
  }, []);

  const place = [profile.location?.city, profile.location?.province].filter(Boolean).join(', ');

  return (
    <div className="d-grid gap-4">
      <div className="row g-4">
        <div className="col-lg-7">
          <div className="card card-elevated h-100">
            <div className="card-body p-4">
              <div className="d-flex gap-3 align-items-center mb-3">
                <CompanyLogo name={profile.name} url={profile.logo_url} />
                <div>
                  <h2 className="section-title h4 mb-0">{profile.name}</h2>
                  {profile.tagline && <p className="mb-0 fw-semibold">{profile.tagline}</p>}
                  <p className="small mb-0">
                    {[profile.industry, labelOf(COMPANY_SIZE, profile.size), place]
                      .filter(Boolean)
                      .join(' · ')}
                  </p>
                </div>
              </div>
              {profile.description && <p className="small">{profile.description}</p>}
              {(profile.benefits ?? []).length > 0 && (
                <div className="d-flex flex-wrap gap-1 mb-3">
                  {profile.benefits!.map((b) => (
                    <span
                      key={b}
                      className="badge bg-soft text-magenta border border-primary-subtle"
                    >
                      {b}
                    </span>
                  ))}
                </div>
              )}
              <div className="d-flex flex-wrap gap-2 align-items-center">
                <button
                  type="button"
                  className="btn btn-outline-primary btn-pill btn-sm"
                  onClick={() => onEdit('company')}
                >
                  <i className="bi bi-pencil me-2" aria-hidden="true" />
                  Editar perfil
                </button>
                <button
                  type="button"
                  className="btn btn-link btn-sm"
                  onClick={() => onEdit('branding')}
                >
                  <i className="bi bi-image me-2" aria-hidden="true" />
                  Logo y marca empleadora
                </button>
                <span className="badge text-bg-light border ms-auto">
                  <i
                    className={`bi me-1 ${profile.visibility === 'hidden' ? 'bi-eye-slash' : 'bi-eye'}`}
                    aria-hidden="true"
                  />
                  {profile.visibility === 'hidden' ? 'Oculto' : 'Visible para estudiantes'}
                </span>
              </div>
            </div>
          </div>
        </div>
        <div className="col-lg-5">
          <CompletionCard completion={profile.completion} onGoToStep={onEdit} />
        </div>
      </div>

      <section className="card card-elevated" aria-labelledby="searches-title">
        <div className="card-body p-4">
          <div className="d-flex justify-content-between align-items-center mb-3">
            <h2 id="searches-title" className="section-title h5 mb-0">
              Búsquedas activas
            </h2>
            <div className="d-flex align-items-center gap-2">
              {searches && (
                <span className="badge text-bg-primary rounded-pill">{searches.total}</span>
              )}
              <button
                type="button"
                className="btn btn-sm btn-outline-primary btn-pill"
                onClick={onSearches}
              >
                Ver todas
              </button>
              <button
                type="button"
                className="btn btn-sm btn-primary btn-pill"
                onClick={onNewSearch}
              >
                <i className="bi bi-plus-lg me-1" aria-hidden="true" />
                Nueva búsqueda
              </button>
            </div>
          </div>
          {!searches && !searchError && (
            <span
              className="spinner-border spinner-border-sm text-primary"
              role="status"
              aria-label="Cargando búsquedas"
            />
          )}
          {searchError && <div className="alert alert-danger small mb-0">{searchError}</div>}
          {searches && searches.items.length === 0 && (
            <p className="small mb-0">Todavía no publicaste búsquedas activas.</p>
          )}
          {searches && searches.items.length > 0 && (
            <ul className="list-group list-group-flush">
              {searches.items.map((s) => (
                <li
                  key={s.id}
                  className="list-group-item px-0 d-flex justify-content-between align-items-start gap-3"
                >
                  <div>
                    <strong className="d-block text-body-emphasis">{s.title}</strong>
                    <span className="small">{jobFacts(s).join(' · ')}</span>
                  </div>
                  <span className="badge text-bg-light border flex-shrink-0">
                    {s.vacancies} vacante{s.vacancies === 1 ? '' : 's'}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  );
};
