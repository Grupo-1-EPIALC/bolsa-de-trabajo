import React, { useEffect, useState } from 'react';
import { adminService } from '../../services/adminService';
import { matchingService } from '../../services/matchingService';
import { adminErrorMessage } from '../../admin/users';
import type { Role } from '../../services/session';
import type { RecommendationSettings } from '../../types/matching';

interface AdminDashboardProps {
  onUsers: (role?: Role) => void;
  onSettings: () => void;
}

type Counts = Record<Role, number>;

const CARDS: Array<{ role: Role; label: string; icon: string }> = [
  { role: 'student', label: 'Estudiantes', icon: 'bi-mortarboard' },
  { role: 'company', label: 'Empresas', icon: 'bi-building' },
  { role: 'admin', label: 'Administradores', icon: 'bi-shield-lock' },
];

/** Resumen: cuentas activas por rol y configuración vigente del matching. */
export const AdminDashboard: React.FC<AdminDashboardProps> = ({ onUsers, onSettings }) => {
  const [counts, setCounts] = useState<Counts | null>(null);
  const [settings, setSettings] = useState<RecommendationSettings | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    Promise.all(CARDS.map(({ role }) => adminService.list({ role, size: 1 })))
      .then((lists) => {
        if (!alive) return;
        setCounts(Object.fromEntries(CARDS.map(({ role }, i) => [role, lists[i].total])) as Counts);
      })
      .catch((err) => alive && setError(adminErrorMessage(err, 'No pudimos cargar las cuentas.')));
    // La configuración es opcional en el resumen: si matching no responde, no se muestra.
    matchingService
      .getSettings()
      .then((s) => alive && setSettings(s))
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div className="d-grid gap-4">
      {error && <div className="alert alert-danger">{error}</div>}
      <section aria-labelledby="admin-accounts">
        <h2 id="admin-accounts" className="section-title h4">
          Cuentas activas
        </h2>
        <div className="row g-3">
          {CARDS.map(({ role, label, icon }) => (
            <div className="col-12 col-md-4" key={role}>
              <button
                type="button"
                className="card card-elevated w-100 text-start h-100 border-0"
                onClick={() => onUsers(role)}
              >
                <span className="card-body d-flex align-items-center gap-3">
                  <span className="icon-circle">
                    <i className={`bi ${icon}`} aria-hidden="true" />
                  </span>
                  <span>
                    <span className="d-block display-6 fw-bold lh-1">
                      {counts ? (
                        counts[role]
                      ) : (
                        <span className="spinner-border spinner-border-sm" aria-hidden="true" />
                      )}
                    </span>
                    <span className="d-block">{label}</span>
                  </span>
                </span>
              </button>
            </div>
          ))}
        </div>
        <button type="button" className="btn btn-primary btn-pill mt-3" onClick={() => onUsers()}>
          <i className="bi bi-people me-2" aria-hidden="true" />
          Administrar cuentas
        </button>
      </section>

      <section aria-labelledby="admin-matching">
        <h2 id="admin-matching" className="section-title h4">
          Matching
        </h2>
        <div className="card card-elevated">
          <div className="card-body d-flex flex-wrap justify-content-between align-items-center gap-3">
            <p className="mb-0">
              {settings ? (
                <>
                  Cada estudiante ve <strong>{settings.student_jobs_limit}</strong> ofertas y cada
                  búsqueda, <strong>{settings.company_candidates_limit}</strong> candidatos.
                </>
              ) : (
                'Cuántas ofertas y candidatos se recomiendan.'
              )}
            </p>
            <button type="button" className="btn btn-outline-primary btn-pill" onClick={onSettings}>
              <i className="bi bi-sliders me-2" aria-hidden="true" />
              Configurar
            </button>
          </div>
        </div>
      </section>
    </div>
  );
};
