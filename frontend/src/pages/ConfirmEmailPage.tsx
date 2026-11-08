import React, { useEffect, useState } from 'react';
import { authService } from '../services/authService';
import { errorMessage } from '../services/api';
import { session } from '../services/session';
import portada from '../assets/portada.jpg';

interface ConfirmEmailPageProps {
  token: string;
  onGoToLogin: () => void;
}

export const ConfirmEmailPage: React.FC<ConfirmEmailPageProps> = ({ token, onGoToLogin }) => {
  const [loading, setLoading] = useState(true);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    const processConfirmation = async () => {
      try {
        await authService.confirmEmail(token);
        if (isMounted) {
          // El cambio de mail rota la sesión: limpiamos la sesión actual por seguridad
          session.clear();
          setSuccess(true);
        }
      } catch (err) {
        if (isMounted) {
          setError(errorMessage(err));
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    processConfirmation();

    return () => {
      isMounted = false;
    };
  }, [token]);

  return (
    <section className="auth-section py-5" style={{ backgroundImage: `url(${portada})` }}>
      <div className="container py-lg-4">
        <div className="row justify-content-center">
          <div className="col-lg-6">
            <div className="card card-elevated border-0 shadow-lg">
              <div className="card-body p-4 p-md-5 text-center">
                <div className="mb-4">
                  <span className="badge rounded-circle bg-soft text-magenta p-3 fs-2">
                    <i className="bi bi-envelope-check" aria-hidden="true" />
                  </span>
                </div>

                <h2 className="h4 fw-extrabold mb-3 text-violet">
                  Confirmación de correo electrónico
                </h2>

                {loading && (
                  <div className="py-4">
                    <div className="spinner-border text-primary me-2" role="status" />
                    <p className="text-body-secondary small mt-2">
                      Verificando enlace de confirmación...
                    </p>
                  </div>
                )}

                {!loading && success && (
                  <div className="d-grid gap-3">
                    <div
                      className="alert alert-success d-flex align-items-center justify-content-center gap-2"
                      role="alert"
                    >
                      <i className="bi bi-check-circle-fill fs-5" aria-hidden="true" />
                      <span className="fw-semibold">
                        ¡Tu dirección de correo fue confirmada con éxito!
                      </span>
                    </div>
                    <p className="small text-body-secondary">
                      Tu cuenta ha sido actualizada. Por motivos de seguridad, iniciá sesión
                      nuevamente utilizando tu nueva dirección de correo.
                    </p>
                    <div className="mt-2">
                      <button
                        type="button"
                        className="btn btn-primary btn-pill btn-lg px-4"
                        onClick={onGoToLogin}
                      >
                        <i className="bi bi-box-arrow-in-right me-2" aria-hidden="true" />
                        Iniciar sesión
                      </button>
                    </div>
                  </div>
                )}

                {!loading && error && (
                  <div className="d-grid gap-3">
                    <div
                      className="alert alert-danger d-flex align-items-center justify-content-center gap-2"
                      role="alert"
                    >
                      <i className="bi bi-exclamation-triangle-fill fs-5" aria-hidden="true" />
                      <span>{error}</span>
                    </div>
                    <p className="small text-body-secondary">
                      El enlace de confirmación es inválido o ha expirado. Si solicitaste un cambio
                      de correo reciente, intentá realizar la solicitud nuevamente desde tu panel.
                    </p>
                    <div className="mt-2">
                      <button
                        type="button"
                        className="btn btn-outline-primary btn-pill px-4"
                        onClick={onGoToLogin}
                      >
                        Volver al inicio
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
