import React from 'react';

interface ProfileStartProps {
  onImportCv: () => void;
  onManual: () => void;
  busy?: boolean;
}

/** Estudiante sin perfil (404 PROFILE_NOT_FOUND): elige cómo empezar. */
export const ProfileStart: React.FC<ProfileStartProps> = ({ onImportCv, onManual, busy }) => (
  <div>
    <div className="text-center mb-4">
      <span className="eyebrow mb-2">Alta de perfil</span>
      <h2 className="section-title h2">¿Cómo querés armar tu perfil?</h2>
      <p className="mb-0">
        Con tu perfil completo vas a recibir ofertas recomendadas y tu CV listo.
      </p>
    </div>
    <div className="row g-4 justify-content-center">
      <div className="col-md-6 col-lg-5">
        <div className="card feature-card h-100 p-4 border-primary-subtle">
          <span className="badge text-bg-primary align-self-start mb-3">Recomendado</span>
          <span className="icon-circle mb-3">
            <i className="bi bi-file-earmark-arrow-up" aria-hidden="true" />
          </span>
          <h3 className="h5 fw-bold">Importar desde mi CV</h3>
          <p className="small">
            Subí tu CV (PDF, DOCX, DOC o MD, hasta 5 MB). La IA detecta tus datos, competencias,
            experiencia y estudios, y vos revisás todo antes de guardar.
          </p>
          <button
            type="button"
            className="btn btn-primary btn-pill mt-auto"
            onClick={onImportCv}
            disabled={busy}
          >
            <i className="bi bi-upload me-2" aria-hidden="true" />
            Subir mi CV
          </button>
        </div>
      </div>
      <div className="col-md-6 col-lg-5">
        <div className="card feature-card h-100 p-4">
          <span className="badge text-bg-light border align-self-start mb-3">Manual</span>
          <span className="icon-circle mb-3">
            <i className="bi bi-pencil-square" aria-hidden="true" />
          </span>
          <h3 className="h5 fw-bold">Cargar mis datos a mano</h3>
          <p className="small">
            Completá tus datos personales, competencias, experiencia, estudios, preferencias
            laborales y privacidad en tres pasos.
          </p>
          <button
            type="button"
            className="btn btn-outline-primary btn-pill mt-auto"
            onClick={onManual}
            disabled={busy}
          >
            {busy && <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />}
            Empezar a cargar
          </button>
        </div>
      </div>
    </div>
  </div>
);
