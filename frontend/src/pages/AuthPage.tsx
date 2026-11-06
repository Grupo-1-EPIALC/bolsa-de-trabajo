import React from 'react';
import portada from '../assets/portada.jpg';
import { AuthForm } from '../components/AuthForm';
import type { AuthMode } from '../navigation';
import type { SessionUser } from '../services/session';

interface AuthPageProps {
  mode: AuthMode;
  onSuccess: (user: SessionUser, mode: AuthMode) => void;
}

const BENEFITS = [
  'Perfil completo a partir de tu CV',
  'Puntaje de compatibilidad por reglas',
  'Sugerencias de formación con IA',
];

export const AuthPage: React.FC<AuthPageProps> = ({ mode, onSuccess }) => (
  <section className="auth-section py-5" style={{ backgroundImage: `url(${portada})` }}>
    <div className="container py-lg-4">
      <div className="row align-items-center g-5">
        <div className="col-lg-6 d-none d-lg-block">
          <span className="eyebrow text-white mb-3">Bolsa de trabajo</span>
          <h1 className="mb-3">Sumate y encontrá tu próxima oportunidad</h1>
          <ul className="list-unstyled d-grid gap-2 lead mb-0">
            {BENEFITS.map((b) => (
              <li key={b}>
                <i className="bi bi-check-circle-fill text-white me-2" aria-hidden="true" />
                {b}
              </li>
            ))}
          </ul>
        </div>
        <div className="col-lg-5 offset-lg-1">
          {/* key: remonta el formulario si se cambia de modo desde la cabecera */}
          <AuthForm key={mode} initialMode={mode} onSuccess={onSuccess} />
        </div>
      </div>
    </div>
  </section>
);
