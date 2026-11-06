import React from 'react';
import portada from '../assets/portada.jpg';
import type { AuthMode } from '../navigation';

interface LandingPageProps {
  onAuth: (mode: AuthMode) => void;
}

const FEATURES = [
  {
    icon: 'bi-file-earmark-person',
    title: 'Subí tu CV',
    text: 'Cargá tu CV en PDF, DOCX o MD. La IA te sugiere datos para completar tu perfil y vos decidís qué aceptar.',
  },
  {
    icon: 'bi-shield-check',
    title: 'Puntaje transparente',
    text: 'La compatibilidad con cada oferta la calcula un motor de reglas auditable, con el desglose de cada criterio.',
  },
  {
    icon: 'bi-stars',
    title: 'Recomendaciones con IA',
    text: 'Recibí cursos, proyectos y consejos para cerrar las brechas de competencias que te pide el mercado.',
  },
  {
    icon: 'bi-building',
    title: 'Para empresas',
    text: 'Publicá búsquedas con requisitos obligatorios y deseables, y encontrá candidatos ordenados por compatibilidad.',
  },
];

const STEPS = [
  { title: 'Creá tu cuenta', text: 'Como estudiante/graduado o como empresa.' },
  {
    title: 'Completá tu perfil',
    text: 'Competencias, experiencia, educación e idiomas.',
  },
  {
    title: 'Encontrá tu match',
    text: 'Mirá tu puntaje por reglas y las sugerencias de la IA.',
  },
];

export const LandingPage: React.FC<LandingPageProps> = ({ onAuth }) => (
  <>
    {/* Portada */}
    <section className="hero" style={{ backgroundImage: `url(${portada})` }}>
      <div className="container pb-5">
        <div className="hero-label d-flex flex-column flex-lg-row align-items-lg-center gap-3 gap-lg-4">
          <div className="flex-grow-1">
            <h1 className="mb-1">Tu primer paso profesional empieza acá</h1>
            <p className="mb-0">
              Conectamos estudiantes y graduados con empresas: compatibilidad por reglas claras y
              recomendaciones de IA.
            </p>
          </div>
          <div className="d-flex flex-wrap flex-lg-column gap-2 flex-shrink-0">
            <button
              type="button"
              className="btn btn-on-magenta btn-pill btn-sm"
              onClick={() => onAuth('register')}
            >
              Registrate gratis
              <i className="bi bi-arrow-right ms-2" aria-hidden="true" />
            </button>
            <button
              type="button"
              className="btn btn-outline-light btn-pill btn-sm"
              onClick={() => onAuth('login')}
            >
              <i className="bi bi-box-arrow-in-right me-2" aria-hidden="true" />
              Ya tengo cuenta
            </button>
          </div>
        </div>
      </div>
    </section>

    {/* Qué ofrecemos */}
    <section className="py-5 bg-white">
      <div className="container py-lg-4">
        <div className="text-center mb-5">
          <span className="eyebrow mb-2">Qué ofrecemos</span>
          <h2 className="section-title display-6">Una bolsa de trabajo pensada para vos</h2>
        </div>
        <div className="row g-4">
          {FEATURES.map((f) => (
            <div className="col-sm-6 col-lg-3" key={f.title}>
              <div className="card feature-card h-100 p-4">
                <span className="icon-circle mb-3">
                  <i className={`bi ${f.icon}`} aria-hidden="true" />
                </span>
                <h3 className="h5 fw-bold">{f.title}</h3>
                <p className="mb-0 small">{f.text}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>

    {/* Cómo funciona */}
    <section className="py-5">
      <div className="container py-lg-4">
        <div className="row align-items-center g-5">
          <div className="col-lg-5">
            <span className="eyebrow mb-2">Cómo funciona</span>
            <h2 className="section-title display-6 mb-4">Tres pasos para empezar</h2>
            <p className="mb-0">
              Separamos siempre lo que calcula el sistema de lo que sugiere la IA: el puntaje
              aparece con el sello <span className="badge badge-rules">Calculado por reglas</span> y
              las sugerencias con <span className="badge badge-ai">Sugerido por IA</span>.
            </p>
          </div>
          <div className="col-lg-7">
            <ol className="list-unstyled d-grid gap-3 mb-0">
              {STEPS.map((s, i) => (
                <li key={s.title} className="card card-elevated p-3 p-md-4">
                  <div className="d-flex align-items-center gap-3">
                    <span className="step-number" aria-hidden="true">
                      {i + 1}
                    </span>
                    <div>
                      <h3 className="h6 fw-bold mb-1">{s.title}</h3>
                      <p className="mb-0 small">{s.text}</p>
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </div>
    </section>

    {/* Banda de llamado a la acción */}
    <section className="cta-band py-5">
      <div className="container d-flex flex-column flex-lg-row align-items-lg-center justify-content-between gap-4">
        <div>
          <span className="eyebrow mb-2">¿Sos empresa?</span>
          <h2 className="h1 fw-extrabold mb-2">Publicá tus búsquedas y encontrá talento</h2>
          <p className="mb-0">Registrá tu organización con CUIT y empezá a recibir candidatos.</p>
        </div>
        <button
          type="button"
          className="btn btn-primary btn-pill btn-lg flex-shrink-0"
          onClick={() => onAuth('register')}
        >
          Inscribite ya
        </button>
      </div>
    </section>
  </>
);
