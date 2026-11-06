import React, { useState } from 'react';
import { authService, PASSWORD_MIN_LENGTH } from '../services/authService';
import { errorMessage, validationMessages } from '../services/api';
import type { AuthMode } from '../navigation';
import type { SessionUser } from '../services/session';

interface AuthFormProps {
  initialMode?: AuthMode;
  onSuccess: (user: SessionUser, mode: AuthMode) => void;
}

interface IconInputProps {
  id: string;
  label: string;
  icon: string;
  type?: string;
  value: string;
  placeholder: string;
  autoComplete?: string;
  hint?: string;
  minLength?: number;
  maxLength?: number;
  onChange: (value: string) => void;
}

const IconInput: React.FC<IconInputProps> = ({
  id,
  label,
  icon,
  type = 'text',
  value,
  placeholder,
  autoComplete,
  hint,
  minLength,
  maxLength,
  onChange,
}) => (
  <div>
    <label htmlFor={id} className="form-label">
      {label}
    </label>
    <div className="input-group">
      <span className="input-group-text bg-white text-magenta">
        <i className={`bi ${icon}`} aria-hidden="true" />
      </span>
      <input
        id={id}
        type={type}
        required
        className="form-control"
        value={value}
        placeholder={placeholder}
        autoComplete={autoComplete}
        minLength={minLength}
        maxLength={maxLength}
        aria-describedby={hint ? `${id}-hint` : undefined}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
    {hint && (
      <div id={`${id}-hint`} className="form-text">
        {hint}
      </div>
    )}
  </div>
);

export const AuthForm: React.FC<AuthFormProps> = ({ initialMode = 'login', onSuccess }) => {
  const [mode, setMode] = useState<AuthMode>(initialMode);
  const [role, setRole] = useState<'student' | 'company'>('student');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [password2, setPassword2] = useState('');
  const [legalName, setLegalName] = useState('');
  const [cuit, setCuit] = useState('');
  const [activity, setActivity] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<{ message: string; items: string[] } | null>(null);

  const isRegister = mode === 'register';

  const switchMode = (next: AuthMode) => {
    setMode(next);
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (isRegister) {
      if (password.length < PASSWORD_MIN_LENGTH) {
        setError({
          message: `La contraseña debe tener al menos ${PASSWORD_MIN_LENGTH} caracteres.`,
          items: [],
        });
        return;
      }
      if (password !== password2) {
        setError({ message: 'Las contraseñas no coinciden.', items: [] });
        return;
      }
      if (role === 'company' && !/^\d{11}$/.test(cuit)) {
        setError({ message: 'El CUIT son 11 dígitos, sin guiones.', items: [] });
        return;
      }
    }

    setLoading(true);
    try {
      const user = isRegister
        ? await authService.register({
            email,
            password,
            role,
            ...(role === 'company' ? { company: { legal_name: legalName, cuit, activity } } : {}),
          })
        : await authService.login({ email, password });
      onSuccess(user, mode);
    } catch (err) {
      setError({ message: errorMessage(err), items: validationMessages(err) });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card card-elevated">
      <div className="card-body p-4 p-md-5">
        {/* Selector Iniciar sesión / Registrarse */}
        <ul className="nav nav-pills nav-fill bg-soft rounded-pill p-1 mb-4" role="tablist">
          <li className="nav-item" role="presentation">
            <button
              type="button"
              role="tab"
              aria-selected={!isRegister}
              className={`nav-link rounded-pill ${!isRegister ? 'active' : ''}`}
              onClick={() => switchMode('login')}
            >
              <i className="bi bi-box-arrow-in-right me-2" aria-hidden="true" />
              Iniciar sesión
            </button>
          </li>
          <li className="nav-item" role="presentation">
            <button
              type="button"
              role="tab"
              aria-selected={isRegister}
              className={`nav-link rounded-pill ${isRegister ? 'active' : ''}`}
              onClick={() => switchMode('register')}
            >
              <i className="bi bi-person-plus me-2" aria-hidden="true" />
              Registrarse
            </button>
          </li>
        </ul>

        <h2 className="h4 fw-extrabold mb-1">
          {isRegister ? 'Creá tu cuenta' : 'Bienvenido/a de nuevo'}
        </h2>
        <p className="small mb-4">
          {isRegister
            ? 'Después de crear la cuenta vas a armar tu perfil.'
            : 'Ingresá con tu correo y contraseña.'}
        </p>

        <form onSubmit={handleSubmit} className="d-grid gap-3">
          {isRegister && (
            <div>
              <label htmlFor="auth-role" className="form-label">
                Tipo de cuenta
              </label>
              <select
                id="auth-role"
                className="form-select"
                value={role}
                onChange={(e) => setRole(e.target.value as 'student' | 'company')}
              >
                <option value="student">Estudiante / Graduado</option>
                <option value="company">Empresa / Organización</option>
              </select>
            </div>
          )}

          <IconInput
            id="auth-email"
            label="Correo electrónico"
            icon="bi-envelope"
            type="email"
            value={email}
            placeholder="usuario@ejemplo.com"
            autoComplete="email"
            onChange={setEmail}
          />

          <IconInput
            id="auth-password"
            label="Contraseña"
            icon="bi-lock"
            type="password"
            value={password}
            placeholder="••••••••••••"
            autoComplete={isRegister ? 'new-password' : 'current-password'}
            hint={isRegister ? `Mínimo ${PASSWORD_MIN_LENGTH} caracteres.` : undefined}
            minLength={isRegister ? PASSWORD_MIN_LENGTH : undefined}
            maxLength={128}
            onChange={setPassword}
          />

          {isRegister && (
            <IconInput
              id="auth-password2"
              label="Repetí la contraseña"
              icon="bi-lock"
              type="password"
              value={password2}
              placeholder="••••••••••••"
              autoComplete="new-password"
              onChange={setPassword2}
            />
          )}

          {/* Datos de la empresa (HU-02) */}
          {isRegister && role === 'company' && (
            <>
              <IconInput
                id="auth-company"
                label="Razón social"
                icon="bi-building"
                value={legalName}
                placeholder="Empresa Ficticia S.A."
                autoComplete="organization"
                maxLength={200}
                onChange={setLegalName}
              />
              <IconInput
                id="auth-cuit"
                label="CUIT (sin guiones)"
                icon="bi-file-earmark-text"
                value={cuit}
                placeholder="30712345678"
                maxLength={11}
                onChange={(v) => setCuit(v.replace(/\D/g, ''))}
              />
              <IconInput
                id="auth-activity"
                label="Actividad"
                icon="bi-briefcase"
                value={activity}
                placeholder="Desarrollo de software"
                maxLength={160}
                onChange={setActivity}
              />
            </>
          )}

          <button type="submit" disabled={loading} className="btn btn-primary btn-pill btn-lg mt-2">
            {loading && (
              <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />
            )}
            {loading ? 'Procesando...' : isRegister ? 'Crear cuenta' : 'Ingresar'}
          </button>
        </form>

        {error && (
          <div role="alert" className="alert alert-danger small fw-semibold mt-4 mb-0">
            {error.message}
            {error.items.length > 0 && (
              <ul className="mb-0 mt-1 fw-normal">
                {error.items.map((i) => (
                  <li key={i}>{i}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
