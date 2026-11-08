import React, { useCallback, useEffect, useState } from 'react';
import { AdminUserDetail } from './AdminUserDetail';
import { Pagination } from '../jobs/Pagination';
import { SelectField, Switch } from '../form/Fields';
import { adminService } from '../../services/adminService';
import { ROLE_LABELS, adminErrorMessage, displayName } from '../../admin/users';
import { RoleBadge, StatusBadge } from './AdminBadges';
import { dateLabel } from '../../jobs/format';
import type { Role } from '../../services/session';
import type { AdminUser, AdminUserList } from '../../types/admin';

interface AdminUsersProps {
  currentUserId: string;
  /** Filtro de rol inicial (desde el resumen del panel). */
  initialRole?: Role;
  onNotice: (message: string) => void;
}

/** Cuentas (contracts/auth.md, parte A §7): buscar, filtrar y abrir el detalle de cada una. */
export const AdminUsers: React.FC<AdminUsersProps> = ({ currentUserId, initialRole, onNotice }) => {
  const [role, setRole] = useState<Role | ''>(initialRole ?? '');
  const [search, setSearch] = useState('');
  const [q, setQ] = useState('');
  const [includeDeleted, setIncludeDeleted] = useState(false);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<AdminUserList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<AdminUser | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await adminService.list({
        role: role || undefined,
        q,
        include_deleted: includeDeleted,
        page,
      });
      // Si un borrado dejó la página vacía, volver a la anterior.
      if (result.items.length === 0 && page > 1) setPage(page - 1);
      else setData(result);
    } catch (err) {
      setError(adminErrorMessage(err, 'No pudimos cargar las cuentas.'));
    } finally {
      setLoading(false);
    }
  }, [role, q, includeDeleted, page]);

  useEffect(() => {
    if (!selected) load();
  }, [load, selected]);

  const applySearch = (event: React.FormEvent) => {
    event.preventDefault();
    setPage(1);
    setQ(search);
  };

  if (selected) {
    return (
      <AdminUserDetail
        key={selected.id}
        user={selected}
        currentUserId={currentUserId}
        onBack={() => setSelected(null)}
        onChanged={(updated, message) => {
          setSelected(updated);
          onNotice(message);
        }}
        onDeleted={(message) => {
          onNotice(message);
          setSelected(null);
        }}
      />
    );
  }

  return (
    <div className="d-grid gap-3">
      <form className="card card-elevated" onSubmit={applySearch} role="search">
        <div className="card-body row g-3 align-items-end">
          <div className="col-12 col-md-5">
            <label htmlFor="admin-search" className="form-label">
              Buscar
            </label>
            <div className="input-group">
              <input
                id="admin-search"
                type="search"
                className="form-control"
                placeholder="Email, razón social o CUIT"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <button type="submit" className="btn btn-primary">
                <i className="bi bi-search" aria-hidden="true" />
                <span className="visually-hidden">Buscar</span>
              </button>
            </div>
          </div>
          <SelectField
            className="col-6 col-md-3"
            label="Rol"
            value={role}
            options={ROLE_LABELS}
            placeholder="Todos"
            onChange={(v) => {
              setPage(1);
              setRole(v as Role | '');
            }}
          />
          <div className="col-6 col-md-4 pb-md-2">
            <Switch
              label="Incluir cuentas borradas"
              checked={includeDeleted}
              onChange={(v) => {
                setPage(1);
                setIncludeDeleted(v);
              }}
            />
          </div>
        </div>
      </form>

      {error && (
        <div className="alert alert-danger d-flex justify-content-between align-items-center">
          <span>{error}</span>
          <button type="button" className="btn btn-sm btn-primary btn-pill" onClick={load}>
            Reintentar
          </button>
        </div>
      )}

      {!data && loading && (
        <div className="text-center py-5">
          <span
            className="spinner-border text-primary"
            role="status"
            aria-label="Cargando cuentas"
          />
        </div>
      )}

      {data && (
        <div className="card card-elevated">
          <div className="card-body">
            <p className="small text-body-secondary mb-3" aria-live="polite">
              {data.total === 0
                ? 'No hay cuentas con esos filtros.'
                : `${data.total} ${data.total === 1 ? 'cuenta' : 'cuentas'}`}
              {loading && (
                <span className="spinner-border spinner-border-sm ms-2" aria-hidden="true" />
              )}
            </p>
            {data.items.length > 0 && (
              <div className="table-responsive">
                <table className="table align-middle mb-0">
                  <caption className="visually-hidden">Cuentas de la bolsa de trabajo</caption>
                  <thead>
                    <tr>
                      <th scope="col">Cuenta</th>
                      <th scope="col">Rol</th>
                      <th scope="col" className="d-none d-md-table-cell">
                        Alta
                      </th>
                      <th scope="col">Estado</th>
                      <th scope="col">
                        <span className="visually-hidden">Acciones</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((u) => (
                      <tr key={u.id}>
                        <td>
                          <div className="fw-semibold text-break">{displayName(u)}</div>
                          {u.company && (
                            <div className="small text-body-secondary text-break">{u.email}</div>
                          )}
                          {u.id === currentUserId && (
                            <span className="badge rounded-pill text-bg-light border">Vos</span>
                          )}
                        </td>
                        <td>
                          <RoleBadge role={u.role} />
                        </td>
                        <td className="d-none d-md-table-cell small">{dateLabel(u.created_at)}</td>
                        <td>
                          <StatusBadge user={u} />
                        </td>
                        <td className="text-end">
                          <button
                            type="button"
                            className="btn btn-sm btn-outline-primary btn-pill"
                            onClick={() => setSelected(u)}
                            aria-label={`Ver la cuenta ${displayName(u)}`}
                          >
                            Ver
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {data && (
        <Pagination
          page={data.page}
          pages={data.pages}
          onPage={setPage}
          label="Páginas de cuentas"
        />
      )}
    </div>
  );
};
