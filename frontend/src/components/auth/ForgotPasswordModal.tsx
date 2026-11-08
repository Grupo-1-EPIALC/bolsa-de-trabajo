import React, { useState } from 'react';
import { authService } from '../../services/authService';
import { errorMessage } from '../../services/api';

interface ForgotPasswordModalProps {
  onClose: () => void;
}

export const ForgotPasswordModal: React.FC<ForgotPasswordModalProps> = ({ onClose }) => {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await authService.requestPasswordReset(email);
      setSent(true);
    } catch (err) {
      // El backend siempre responde exitoso independientemente de si el email existe (RNF-05),
      // pero capturamos errores de red/servidor (500/503).
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card card-elevated border-0 shadow-lg">
      <div className="card-body p-4 p-md-5">
        <div className="d-flex justify-content-between align-items-center mb-4">
          <h2 className="h4 fw-extrabold mb-0 text-violet">Recuperar contraseña</h2>
          <button type="button" className="btn-close" aria-label="Cerrar" onClick={onClose} />
        </div>

        {sent ? (
          <div className="alert alert-success d-flex align-items-start gap-2" role="alert">
            <i className="bi bi-check-circle-fill fs-5 flex-shrink-0" aria-hidden="true" />
            <div>
              <strong>Revisá tu casilla de correo.</strong>
              <p className="mb-0 small">
                Si el email se encuentra registrado en el sistema, recibirás un enlace válido por 1
                hora para restablecer tu clave.
              </p>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="d-grid gap-3">
            <p className="small text-body-secondary mb-2">
              Ingresá el correo electrónico asociado a tu cuenta para recibir el enlace de
              recuperación.
            </p>

            {error && <div className="alert alert-danger small">{error}</div>}

            <div>
              <label htmlFor="reset-email" className="form-label">
                Correo electrónico
              </label>
              <div className="input-group">
                <span className="input-group-text bg-white text-magenta">
                  <i className="bi bi-envelope" aria-hidden="true" />
                </span>
                <input
                  id="reset-email"
                  type="email"
                  required
                  className="form-control"
                  value={email}
                  placeholder="usuario@ejemplo.com"
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
            </div>

            <div className="d-flex justify-content-end gap-2 mt-3">
              <button type="button" className="btn btn-outline-primary btn-pill" onClick={onClose}>
                Cancelar
              </button>
              <button type="submit" className="btn btn-primary btn-pill" disabled={loading}>
                {loading && (
                  <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />
                )}
                Enviar enlace
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
