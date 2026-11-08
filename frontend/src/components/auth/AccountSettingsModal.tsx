// src/components/auth/AccountSettingsModal.tsx
import React, { useState } from 'react';
import { authService, PASSWORD_MIN_LENGTH } from '../../services/authService';
import { errorMessage } from '../../services/api';
import { session, SessionUser } from '../../services/session';

interface AccountSettingsModalProps {
  user: SessionUser;
  onClose: () => void;
}

export const AccountSettingsModal: React.FC<AccountSettingsModalProps> = ({ user, onClose }) => {
  const [tab, setTab] = useState<'password' | 'email'>('password');

  // Formulario Cambio de Contraseña
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newPasswordConfirm, setNewPasswordConfirm] = useState('');
  const [passLoading, setPassLoading] = useState(false);
  const [passError, setPassError] = useState<string | null>(null);

  // Formulario Cambio de Email
  const [newEmail, setNewEmail] = useState('');
  const [emailPassword, setEmailPassword] = useState('');
  const [emailLoading, setEmailLoading] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  const [emailError, setEmailError] = useState<string | null>(null);

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword.length < PASSWORD_MIN_LENGTH) {
      setPassError(`La nueva contraseña debe tener al menos ${PASSWORD_MIN_LENGTH} caracteres.`);
      return;
    }
    if (newPassword !== newPasswordConfirm) {
      setPassError('Las nuevas contraseñas no coinciden.');
      return;
    }

    setPassLoading(true);
    setPassError(null);
    try {
      await authService.changePassword(currentPassword, newPassword);
      // El cambio de clave invalida la sesión por seguridad (contrato §6)
      session.clear();
      onClose();
    } catch (err) {
      setPassError(errorMessage(err));
    } finally {
      setPassLoading(false);
    }
  };

  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setEmailLoading(true);
    setEmailError(null);
    setEmailSent(false);
    try {
      await authService.requestEmailChange(newEmail, emailPassword);
      setEmailSent(true);
      setNewEmail('');
      setEmailPassword('');
    } catch (err) {
      setEmailError(errorMessage(err));
    } finally {
      setEmailLoading(false);
    }
  };

  return (
    <div className="card card-elevated border-0 shadow-lg">
      <div className="card-body p-4 p-md-5">
        <div className="d-flex justify-content-between align-items-center mb-3">
          <div>
            <h2 className="h4 fw-extrabold mb-0 text-violet">Mi cuenta</h2>
            <span className="small text-body-secondary">
              {user.email} ({user.role})
            </span>
          </div>
          <button type="button" className="btn-close" aria-label="Cerrar" onClick={onClose} />
        </div>

        {/* Pestañas de navegación interna */}
        <ul className="nav nav-pills nav-fill bg-soft rounded-pill p-1 mb-4" role="tablist">
          <li className="nav-item" role="presentation">
            <button
              type="button"
              className={`nav-link rounded-pill ${tab === 'password' ? 'active' : ''}`}
              onClick={() => setTab('password')}
            >
              <i className="bi bi-key me-2" aria-hidden="true" />
              Cambiar contraseña
            </button>
          </li>
          <li className="nav-item" role="presentation">
            <button
              type="button"
              className={`nav-link rounded-pill ${tab === 'email' ? 'active' : ''}`}
              onClick={() => setTab('email')}
            >
              <i className="bi bi-envelope me-2" aria-hidden="true" />
              Cambiar correo
            </button>
          </li>
        </ul>

        {/* TAB 1: Cambiar contraseña */}
        {tab === 'password' && (
          <form onSubmit={handlePasswordSubmit} className="d-grid gap-3">
            {passError && (
              <div className="alert alert-danger small mb-0" role="alert">
                {passError}
              </div>
            )}

            <div>
              <label htmlFor="curr-pass" className="form-label">
                Contraseña actual
              </label>
              <div className="input-group">
                <span className="input-group-text bg-white text-magenta">
                  <i className="bi bi-lock" aria-hidden="true" />
                </span>
                <input
                  id="curr-pass"
                  type="password"
                  required
                  className="form-control"
                  value={currentPassword}
                  placeholder="••••••••••••"
                  onChange={(e) => setCurrentPassword(e.target.value)}
                />
              </div>
            </div>

            <div>
              <label htmlFor="new-pass" className="form-label">
                Nueva contraseña
              </label>
              <div className="input-group">
                <span className="input-group-text bg-white text-magenta">
                  <i className="bi bi-shield-lock" aria-hidden="true" />
                </span>
                <input
                  id="new-pass"
                  type="password"
                  required
                  className="form-control"
                  value={newPassword}
                  placeholder="••••••••••••"
                  minLength={PASSWORD_MIN_LENGTH}
                  onChange={(e) => setNewPassword(e.target.value)}
                />
              </div>
              <div className="form-text small">Mínimo {PASSWORD_MIN_LENGTH} caracteres.</div>
            </div>

            <div>
              <label htmlFor="new-pass-confirm" className="form-label">
                Confirmar nueva contraseña
              </label>
              <div className="input-group">
                <span className="input-group-text bg-white text-magenta">
                  <i className="bi bi-shield-lock-fill" aria-hidden="true" />
                </span>
                <input
                  id="new-pass-confirm"
                  type="password"
                  required
                  className="form-control"
                  value={newPasswordConfirm}
                  placeholder="••••••••••••"
                  onChange={(e) => setNewPasswordConfirm(e.target.value)}
                />
              </div>
            </div>

            <div className="alert alert-warning small d-flex gap-2 align-items-center mb-0">
              <i
                className="bi bi-exclamation-triangle-fill fs-5 flex-shrink-0"
                aria-hidden="true"
              />
              <span>Al cambiar tu clave se cerrarán las sesiones en todos los dispositivos.</span>
            </div>

            <div className="d-flex justify-content-end gap-2 mt-2">
              <button type="button" className="btn btn-outline-primary btn-pill" onClick={onClose}>
                Cancelar
              </button>
              <button type="submit" className="btn btn-primary btn-pill" disabled={passLoading}>
                {passLoading && (
                  <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />
                )}
                Actualizar contraseña
              </button>
            </div>
          </form>
        )}

        {/* TAB 2: Cambiar correo electrónico */}
        {tab === 'email' && (
          <form onSubmit={handleEmailSubmit} className="d-grid gap-3">
            {emailSent && (
              <div className="alert alert-success d-flex align-items-start gap-2" role="alert">
                <i className="bi bi-check-circle-fill fs-5 flex-shrink-0" aria-hidden="true" />
                <div>
                  <strong>Enlace enviado.</strong>
                  <p className="mb-0 small">
                    Enviamos un correo a la nueva casilla para confirmar el cambio.
                  </p>
                </div>
              </div>
            )}

            {emailError && (
              <div className="alert alert-danger small mb-0" role="alert">
                {emailError}
              </div>
            )}

            <div>
              <label htmlFor="new-email" className="form-label">
                Nuevo correo electrónico
              </label>
              <div className="input-group">
                <span className="input-group-text bg-white text-magenta">
                  <i className="bi bi-envelope-at" aria-hidden="true" />
                </span>
                <input
                  id="new-email"
                  type="email"
                  required
                  className="form-control"
                  value={newEmail}
                  placeholder="nuevo@correo.com"
                  onChange={(e) => setNewEmail(e.target.value)}
                />
              </div>
            </div>

            <div>
              <label htmlFor="confirm-email-pass" className="form-label">
                Contraseña actual para confirmar
              </label>
              <div className="input-group">
                <span className="input-group-text bg-white text-magenta">
                  <i className="bi bi-lock" aria-hidden="true" />
                </span>
                <input
                  id="confirm-email-pass"
                  type="password"
                  required
                  className="form-control"
                  value={emailPassword}
                  placeholder="••••••••••••"
                  onChange={(e) => setEmailPassword(e.target.value)}
                />
              </div>
            </div>

            <div className="d-flex justify-content-end gap-2 mt-2">
              <button type="button" className="btn btn-outline-primary btn-pill" onClick={onClose}>
                Cancelar
              </button>
              <button type="submit" className="btn btn-primary btn-pill" disabled={emailLoading}>
                {emailLoading && (
                  <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />
                )}
                Solicitar cambio
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
