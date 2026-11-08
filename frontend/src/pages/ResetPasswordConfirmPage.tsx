import React, { useState } from 'react';
import { authService, PASSWORD_MIN_LENGTH } from '../services/authService';
import { errorMessage } from '../services/api';
import portada from '../assets/portada.jpg';

interface ResetPasswordConfirmPageProps {
  token: string;
  onSuccess: () => void;
}

export const ResetPasswordConfirmPage: React.FC<ResetPasswordConfirmPageProps> = ({
  token,
  onSuccess,
}) => {
  const [password, setPassword] = useState('');
  const [password2, setPassword2] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < PASSWORD_MIN_LENGTH) {
      setError(`La contraseña debe tener al menos ${PASSWORD_MIN_LENGTH} caracteres.`);
      return;
    }
    if (password !== password2) {
      setError('Las contraseñas no coinciden.');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await authService.confirmPasswordReset(token, password);
      onSuccess();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="auth-section py-5" style={{ backgroundImage: `url(${portada})` }}>
      <div className="container py-lg-4">
        <div className="row justify-content-center">
          <div className="col-lg-5">
            <div className="card card-elevated">
              <div className="card-body p-4 p-md-5">
                <h2 className="h4 fw-extrabold mb-2 text-violet">Crear nueva contraseña</h2>
                <p className="small mb-4 text-body-secondary">
                  Ingresá tu nueva clave de acceso (mínimo {PASSWORD_MIN_LENGTH} caracteres).
                </p>

                {error && <div className="alert alert-danger small mb-3">{error}</div>}

                <form onSubmit={handleSubmit} className="d-grid gap-3">
                  <div>
                    <label htmlFor="new-pass" className="form-label">
                      Nueva contraseña
                    </label>
                    <div className="input-group">
                      <span className="input-group-text bg-white text-magenta">
                        <i className="bi bi-lock" aria-hidden="true" />
                      </span>
                      <input
                        id="new-pass"
                        type="password"
                        required
                        className="form-control"
                        value={password}
                        placeholder="••••••••••••"
                        minLength={PASSWORD_MIN_LENGTH}
                        maxLength={128}
                        onChange={(e) => setPassword(e.target.value)}
                      />
                    </div>
                  </div>

                  <div>
                    <label htmlFor="confirm-pass" className="form-label">
                      Repetir nueva contraseña
                    </label>
                    <div className="input-group">
                      <span className="input-group-text bg-white text-magenta">
                        <i className="bi bi-lock" aria-hidden="true" />
                      </span>
                      <input
                        id="confirm-pass"
                        type="password"
                        required
                        className="form-control"
                        value={password2}
                        placeholder="••••••••••••"
                        onChange={(e) => setPassword2(e.target.value)}
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    className="btn btn-primary btn-pill btn-lg mt-3"
                    disabled={loading}
                  >
                    {loading && (
                      <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />
                    )}
                    Guardar nueva contraseña
                  </button>
                </form>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
