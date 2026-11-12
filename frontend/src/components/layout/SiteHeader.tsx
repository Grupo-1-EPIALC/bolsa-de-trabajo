import React, { useState } from 'react';
import type { AuthMode, StudentSection, View } from '../../navigation';
import type { SessionUser } from '../../services/session';
import { AccountSettingsModal } from '../auth/AccountSettingsModal'; // Ajusta la ruta a tu componente de modal si varía

interface SiteHeaderProps {
  user: SessionUser | null;
  activeView: View;
  section: StudentSection;
  onNavigate: (view: View) => void;
  onSection: (section: StudentSection) => void;
  onAuth: (mode: AuthMode) => void;
  onLogout: () => void;
}

const COMPANY_NAV: Array<{ section: StudentSection; label: string; icon: string }> = [
  { section: 'panel', label: 'Mi empresa', icon: 'bi-building' },
  { section: 'searches', label: 'Búsquedas', icon: 'bi-search' },
  { section: 'profile', label: 'Perfil de la empresa', icon: 'bi-pencil-square' },
];

// Incluye 'jobs' para "Todas las ofertas"
const STUDENT_NAV: Array<{ section: StudentSection; label: string; icon: string }> = [
  { section: 'panel', label: 'Mi panel', icon: 'bi-grid' },
  { section: 'recommendations', label: 'Ofertas para vos', icon: 'bi-briefcase' },
  { section: 'jobs', label: 'Todas las ofertas', icon: 'bi-search' },
  { section: 'profile', label: 'Mi perfil', icon: 'bi-person-vcard' },
];

export const SiteHeader: React.FC<SiteHeaderProps> = ({
  user,
  activeView,
  section,
  onNavigate,
  onSection,
  onAuth,
  onLogout,
}) => {
  const [open, setOpen] = useState(false);
  const [showAccountModal, setShowAccountModal] = useState(false); // Estado devuelto para el modal

  const go = (fn: () => void) => () => {
    fn();
    setOpen(false);
  };

  return (
    <header className="sticky-top">
      {/* Barra superior */}
      <div className="topbar py-2 d-none d-md-block">
        <div className="container d-flex justify-content-between align-items-center">
          <span>
            <i className="bi bi-mortarboard-fill me-2" aria-hidden="true" />
            Portal de empleo para estudiantes y graduados
          </span>
          {user ? (
            /* Botón interactivo sobre el email para activar el modal de cuenta/password */
            <button
              type="button"
              className="btn btn-link text-white text-decoration-none p-0 border-0 shadow-none align-baseline"
              onClick={() => setShowAccountModal(true)}
              title="Configuración de cuenta y cambio de clave"
            >
              <i className="bi bi-person-circle me-1" aria-hidden="true" />
              <span className="fw-semibold">{user.email}</span>
            </button>
          ) : (
            <span className="d-flex gap-3">
              <span>
                <i className="bi bi-shield-check me-1" aria-hidden="true" />
                Matching auditable por reglas
              </span>
              <span>
                <i className="bi bi-stars me-1" aria-hidden="true" />
                Recomendaciones con IA
              </span>
            </span>
          )}
        </div>
      </div>

      <nav className="navbar navbar-expand-lg site-navbar py-2" aria-label="Navegación principal">
        <div className="container">
          <button
            type="button"
            className="navbar-brand d-flex align-items-center gap-2 border-0 bg-transparent p-0"
            onClick={go(() => (user ? onSection('panel') : onNavigate('home')))}
          >
            <span className="brand-mark">
              <i className="bi bi-briefcase-fill" aria-hidden="true" />
            </span>
            <span className="text-start">
              <span className="d-block fs-5">Bolsa de Trabajo</span>
              <span className="brand-sub d-block">Estudiantes · Empresas</span>
            </span>
          </button>

          <button
            className="navbar-toggler border-0"
            type="button"
            aria-controls="mainNav"
            aria-expanded={open}
            aria-label={open ? 'Cerrar menú' : 'Abrir menú'}
            onClick={() => setOpen((v) => !v)}
          >
            <i
              className={`bi ${open ? 'bi-x-lg' : 'bi-list'} fs-2 text-violet`}
              aria-hidden="true"
            />
          </button>

          <div className={`collapse navbar-collapse ${open ? 'show' : ''}`} id="mainNav">
            <ul className="navbar-nav ms-auto align-items-lg-center gap-lg-2 py-3 py-lg-0">
              {user ? (
                <>
                  {(user.role === 'student'
                    ? STUDENT_NAV
                    : user.role === 'company'
                      ? COMPANY_NAV
                      : []
                  ).map((item) => (
                    <li className="nav-item" key={item.section}>
                      <button
                        type="button"
                        className={`nav-link ${section === item.section ? 'active' : ''}`}
                        aria-current={section === item.section ? 'page' : undefined}
                        onClick={go(() => onSection(item.section))}
                      >
                        <i className={`bi ${item.icon} me-2`} aria-hidden="true" />
                        {item.label}
                      </button>
                    </li>
                  ))}
                  <li className="nav-item ms-lg-2">
                    <button
                      type="button"
                      className="btn btn-outline-danger btn-pill btn-sm"
                      onClick={go(onLogout)}
                    >
                      <i className="bi bi-box-arrow-right me-1" aria-hidden="true" />
                      Cerrar sesión
                    </button>
                  </li>
                </>
              ) : (
                <>
                  <li className="nav-item">
                    <button
                      type="button"
                      className={`nav-link ${activeView === 'home' ? 'active' : ''}`}
                      onClick={go(() => onNavigate('home'))}
                    >
                      Inicio
                    </button>
                  </li>
                  <li className="nav-item ms-lg-2">
                    <button
                      type="button"
                      className="btn btn-outline-primary btn-pill btn-sm"
                      onClick={go(() => onAuth('login'))}
                    >
                      Ingresar
                    </button>
                  </li>
                  <li className="nav-item">
                    <button
                      type="button"
                      className="btn btn-primary btn-pill btn-sm"
                      onClick={go(() => onAuth('register'))}
                    >
                      Registrate
                    </button>
                  </li>
                </>
              )}
            </ul>
          </div>
        </div>
      </nav>

      {/* Modal de configuración de la cuenta superpuesto (restaurado) */}
      {showAccountModal && user && (
        <div
          className="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center p-3"
          style={{ backgroundColor: 'rgba(0, 0, 0, 0.5)', zIndex: 1050 }}
        >
          <div style={{ maxWidth: '30rem', width: '100%' }}>
            <AccountSettingsModal user={user} onClose={() => setShowAccountModal(false)} />
          </div>
        </div>
      )}
    </header>
  );
};
