import React from 'react';
import { CompletionCard } from './CompletionCard';
import { CvDownloads } from './CvDownloads';
import type { ProfileStep, ProfileView } from '../../types/profile';

interface ProfileDashboardProps {
  profile: ProfileView;
  onRecommendations: () => void;
  onEdit: (step: ProfileStep) => void;
  onReviewSuggestions: () => void;
  onImportCv: () => void;
}

/** Panel del estudiante con perfil: recomendaciones, modificar perfil y descargar el CV. */
export const ProfileDashboard: React.FC<ProfileDashboardProps> = ({
  profile,
  onRecommendations,
  onEdit,
  onReviewSuggestions,
  onImportCv,
}) => {
  const complete = profile.completion.status === 'complete';
  const skills = profile.skills ?? [];

  return (
    <div className="d-grid gap-4">
      {profile.has_cv_suggestions && (
        <div className="panel-ai rounded-3 p-3 d-flex flex-wrap justify-content-between align-items-center gap-2">
          <span className="small">
            <span className="badge badge-ai me-2">
              <i className="bi bi-stars me-1" aria-hidden="true" />
              Sugerido por IA
            </span>
            Tenés datos detectados en tu CV que todavía no revisaste.
          </span>
          <button
            type="button"
            className="btn btn-sm btn-primary btn-pill"
            onClick={onReviewSuggestions}
          >
            Ver datos detectados
          </button>
        </div>
      )}

      <div className="row g-4">
        {/* Ofertas recomendadas */}
        <div className="col-lg-4">
          <div className="card feature-card h-100 p-4">
            <span className="icon-circle mb-3">
              <i className="bi bi-briefcase" aria-hidden="true" />
            </span>
            <h2 className="h5 fw-bold">Ofertas para vos</h2>
            <p className="small">
              Las búsquedas activas ordenadas por compatibilidad con tu perfil, con el puntaje
              calculado por reglas y consejos de la IA.
            </p>
            {!complete && (
              <p className="small text-warning-emphasis">
                <i className="bi bi-exclamation-triangle me-1" aria-hidden="true" />
                Completá tu perfil para entrar al matching.
              </p>
            )}
            <button
              type="button"
              className="btn btn-primary btn-pill mt-auto"
              onClick={onRecommendations}
            >
              Ver ofertas recomendadas
              <i className="bi bi-arrow-right ms-2" aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* Modificar perfil */}
        <div className="col-lg-4">
          <div className="card feature-card h-100 p-4">
            <span className="icon-circle mb-3">
              <i className="bi bi-person-gear" aria-hidden="true" />
            </span>
            <h2 className="h5 fw-bold">Modificar mi perfil</h2>
            <p className="small">
              Actualizá tus datos, competencias, preferencias laborales y privacidad.
            </p>
            <div className="d-grid gap-2 mt-auto">
              <button
                type="button"
                className="btn btn-outline-primary btn-pill"
                onClick={() => onEdit('cv')}
              >
                <i className="bi bi-pencil me-2" aria-hidden="true" />
                Editar perfil
              </button>
              <button type="button" className="btn btn-link" onClick={onImportCv}>
                <i className="bi bi-file-earmark-arrow-up me-2" aria-hidden="true" />
                Importar datos de un CV nuevo
              </button>
            </div>
          </div>
        </div>

        {/* Descargar CV */}
        <div className="col-lg-4">
          <div className="card feature-card h-100 p-4">
            <span className="icon-circle mb-3">
              <i className="bi bi-file-earmark-person" aria-hidden="true" />
            </span>
            <h2 className="h5 fw-bold">Mi CV</h2>
            <p className="small">
              Un CV moderno y fácil de leer para los filtros con IA, armado con los datos que
              confirmaste.
            </p>
            <div className="mt-auto">
              <CvDownloads enabled={profile.completion.can_generate_cv} />
            </div>
          </div>
        </div>
      </div>

      <div className="row g-4">
        <div className="col-lg-5">
          <CompletionCard completion={profile.completion} onGoToStep={onEdit} />
        </div>
        <div className="col-lg-7">
          <div className="card card-elevated h-100">
            <div className="card-body p-4">
              <h2 className="section-title h5 mb-1">{profile.personal.name || 'Tu perfil'}</h2>
              <p className="mb-3 fw-semibold">{profile.headline}</p>
              {profile.summary && <p className="small">{profile.summary}</p>}
              <h3 className="h6 fw-bold mt-3">Competencias</h3>
              <div className="d-flex flex-wrap gap-2">
                {skills.length === 0 && (
                  <span className="small">Todavía no cargaste competencias.</span>
                )}
                {skills.map((s) => (
                  <span
                    key={s.normalized ?? s.name}
                    className="d-inline-flex align-items-center gap-2 border rounded-pill ps-3 pe-1 py-1 bg-white small fw-semibold text-body-emphasis"
                  >
                    {s.name}
                    <span className="badge rounded-pill text-bg-primary">Nivel {s.level}</span>
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
