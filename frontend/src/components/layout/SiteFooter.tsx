import React from 'react';
import type { AuthMode, StudentSection, View } from '../../navigation';
import type { SessionUser } from '../../services/session';

interface SiteFooterProps {
  user: SessionUser | null;
  onNavigate: (view: View) => void;
  onSection: (section: StudentSection) => void;
  onAuth: (mode: AuthMode) => void;
}

const FooterLink: React.FC<{ onClick: () => void; children: React.ReactNode }> = ({
  onClick,
  children,
}) => (
  <li>
    <button type="button" className="footer-link" onClick={onClick}>
      {children}
    </button>
  </li>
);

export const SiteFooter: React.FC<SiteFooterProps> = ({ user, onNavigate, onSection, onAuth }) => (
  <footer className="site-footer mt-auto">
    <div className="container py-5">
      <div className="row g-4">
        <div className="col-lg-5">
          <div className="d-flex align-items-center gap-2 mb-3">
            <span className="brand-mark">
              <i className="bi bi-briefcase-fill" aria-hidden="true" />
            </span>
            <span className="text-white fw-extrabold fs-5">Bolsa de Trabajo</span>
          </div>
          <p className="mb-0" style={{ maxWidth: '26rem' }}>
            Conectamos estudiantes y graduados con empresas. El puntaje de compatibilidad lo calcula
            un motor de reglas auditable; la IA sólo sugiere cómo mejorar.
          </p>
        </div>

        <div className="col-6 col-lg-3">
          <h2 className="mb-3">Navegación</h2>
          <ul className="list-unstyled d-grid gap-2 mb-0">
            {user?.role === 'student' && (
              <>
                <FooterLink onClick={() => onSection('panel')}>Mi panel</FooterLink>
                <FooterLink onClick={() => onSection('recommendations')}>
                  Ofertas para vos
                </FooterLink>
                <FooterLink onClick={() => onSection('jobs')}>Todas las ofertas</FooterLink>
                <FooterLink onClick={() => onSection('profile')}>Mi perfil</FooterLink>
              </>
            )}
            {!user && (
              <>
                <FooterLink onClick={() => onNavigate('home')}>Inicio</FooterLink>
                <FooterLink onClick={() => onAuth('login')}>Ingresar</FooterLink>
                <FooterLink onClick={() => onAuth('register')}>Crear cuenta</FooterLink>
              </>
            )}
            {user?.role === 'company' && (
              <>
                <FooterLink onClick={() => onSection('panel')}>Mi empresa</FooterLink>
                <FooterLink onClick={() => onSection('searches')}>Búsquedas</FooterLink>
                <FooterLink onClick={() => onSection('profile')}>Perfil de la empresa</FooterLink>
              </>
            )}
            {user?.role === 'admin' && (
              <>
                <FooterLink onClick={() => onSection('panel')}>Panel</FooterLink>
                <FooterLink onClick={() => onSection('users')}>Cuentas</FooterLink>
                <FooterLink onClick={() => onSection('settings')}>
                  Configuración de matching
                </FooterLink>
              </>
            )}
          </ul>
        </div>

        <div className="col-6 col-lg-4">
          <h2 className="mb-3">Transparencia</h2>
          <ul className="list-unstyled d-grid gap-2 mb-0">
            <li>
              <i className="bi bi-shield-check me-2 text-white" aria-hidden="true" />
              Puntaje calculado por reglas
            </li>
            <li>
              <i className="bi bi-stars me-2 text-white" aria-hidden="true" />
              Sugerencias de IA identificadas
            </li>
            <li>
              <i className="bi bi-lock me-2 text-white" aria-hidden="true" />
              Tus datos, bajo tu control
            </li>
          </ul>
        </div>
      </div>
    </div>
    <div className="footer-bottom py-3">
      <div className="container d-flex flex-column flex-md-row justify-content-between gap-2">
        <span>© {new Date().getFullYear()} Bolsa de Trabajo · MVP académico</span>
        <span>Hecho con React + Bootstrap</span>
      </div>
    </div>
  </footer>
);
