import React, { useEffect, useState } from 'react';
import { RoleBadge, StatusBadge } from './AdminBadges';
import { TextField } from '../form/Fields';
import { adminService } from '../../services/adminService';
import {
  UserForm,
  UserFormErrors,
  adminErrorMessage,
  displayName,
  formToUpdate,
  userActions,
  userToForm,
  validateUserForm,
} from '../../admin/users';
import { dateLabel } from '../../jobs/format';
import type { AdminUser } from '../../types/admin';

interface AdminUserDetailProps {
  user: AdminUser;
  currentUserId: string;
  onBack: () => void;
  onChanged: (user: AdminUser, message: string) => void;
  onDeleted: (message: string) => void;
}

type Confirm = 'reset' | 'delete' | null;

const FieldError: React.FC<{ message?: string }> = ({ message }) =>
  message ? (
    <div className="small text-danger mt-1" role="alert">
      {message}
    </div>
  ) : null;

const Fact: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <div className="col-12 col-sm-6">
    <dt className="small text-body-secondary fw-normal">{label}</dt>
    <dd className="mb-0 text-break">{children}</dd>
  </div>
);

/** Detalle de una cuenta con edición, reset forzado de clave y borrado lógico. */
export const AdminUserDetail: React.FC<AdminUserDetailProps> = ({
  user: initial,
  currentUserId,
  onBack,
  onChanged,
  onDeleted,
}) => {
  const [user, setUser] = useState(initial);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<UserForm>(() => userToForm(initial));
  const [errors, setErrors] = useState<UserFormErrors>({});
  const [confirm, setConfirm] = useState<Confirm>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const actions = userActions(user, currentUserId);

  // Datos frescos: el listado pudo quedar viejo.
  useEffect(() => {
    let alive = true;
    adminService
      .get(initial.id)
      .then((fresh) => {
        if (alive) {
          setUser(fresh);
          setForm(userToForm(fresh));
        }
      })
      .catch((err) => alive && setError(adminErrorMessage(err, 'No pudimos cargar la cuenta.')));
    return () => {
      alive = false;
    };
  }, [initial.id]);

  const set = (key: keyof UserForm) => (value: string) => {
    setForm((f) => ({ ...f, [key]: key === 'cuit' ? value.replace(/\D/g, '') : value }));
    setErrors((e) => ({ ...e, [key]: undefined }));
  };

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    const found = validateUserForm(form, user);
    setErrors(found);
    if (Object.keys(found).length) return;
    const changes = formToUpdate(form, user);
    if (!changes) {
      setEditing(false);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const updated = await adminService.update(user.id, changes);
      setUser(updated);
      setForm(userToForm(updated));
      setEditing(false);
      onChanged(updated, 'Cuenta actualizada');
    } catch (err) {
      setError(adminErrorMessage(err, 'No pudimos guardar los cambios.'));
    } finally {
      setBusy(false);
    }
  };

  const resetPassword = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await adminService.resetPassword(user.id);
      setConfirm(null);
      if (result.email_sent) {
        setInfo(`Se invalidó la clave y se mandó el link de recuperación a ${user.email}.`);
        onChanged(user, 'Link de recuperación enviado');
      } else {
        setError('Se invalidó la clave, pero el mail no salió. Probá de nuevo en unos minutos.');
      }
    } catch (err) {
      setError(adminErrorMessage(err, 'No pudimos forzar el cambio de clave.'));
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    setBusy(true);
    setError(null);
    try {
      await adminService.remove(user.id);
      onDeleted(`Cuenta de ${displayName(user)} borrada`);
    } catch (err) {
      setError(adminErrorMessage(err, 'No pudimos borrar la cuenta.'));
      setBusy(false);
    }
  };

  return (
    <div className="d-grid gap-3">
      <div>
        <button type="button" className="btn btn-link px-0" onClick={onBack}>
          <i className="bi bi-arrow-left me-1" aria-hidden="true" />
          Volver a las cuentas
        </button>
      </div>

      <div className="card card-elevated">
        <div className="card-body p-4">
          <div className="d-flex flex-wrap justify-content-between align-items-start gap-2 mb-3">
            <div>
              <h2 className="h4 fw-bold mb-1 text-break">{displayName(user)}</h2>
              <div className="d-flex gap-2">
                <RoleBadge role={user.role} />
                <StatusBadge user={user} />
                {actions.self && (
                  <span className="badge rounded-pill text-bg-light border">Tu cuenta</span>
                )}
              </div>
            </div>
            {!editing && (
              <div className="d-flex flex-wrap gap-2">
                {actions.edit && (
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-primary btn-pill"
                    onClick={() => {
                      setConfirm(null);
                      setEditing(true);
                    }}
                  >
                    <i className="bi bi-pencil me-1" aria-hidden="true" />
                    Editar
                  </button>
                )}
                {actions.resetPassword && (
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-primary btn-pill"
                    onClick={() => setConfirm('reset')}
                  >
                    <i className="bi bi-key me-1" aria-hidden="true" />
                    Forzar cambio de clave
                  </button>
                )}
                {actions.remove && (
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-danger btn-pill"
                    onClick={() => setConfirm('delete')}
                  >
                    <i className="bi bi-trash me-1" aria-hidden="true" />
                    Borrar
                  </button>
                )}
              </div>
            )}
          </div>

          {error && <div className="alert alert-danger small">{error}</div>}
          {info && <div className="alert alert-success small">{info}</div>}

          {confirm === 'reset' && (
            <div className="alert alert-warning" role="alertdialog" aria-labelledby="confirm-reset">
              <p id="confirm-reset" className="mb-2">
                <strong>¿Forzar el cambio de clave de {user.email}?</strong> La clave actual deja de
                funcionar, se cierran todas sus sesiones y le llega un mail para elegir una nueva.
              </p>
              <div className="d-flex gap-2">
                <button
                  type="button"
                  className="btn btn-sm btn-warning btn-pill"
                  onClick={resetPassword}
                  disabled={busy}
                >
                  {busy && (
                    <span className="spinner-border spinner-border-sm me-1" aria-hidden="true" />
                  )}
                  Sí, forzar el cambio
                </button>
                <button
                  type="button"
                  className="btn btn-sm btn-outline-secondary btn-pill"
                  onClick={() => setConfirm(null)}
                  disabled={busy}
                >
                  Cancelar
                </button>
              </div>
            </div>
          )}

          {confirm === 'delete' && (
            <div className="alert alert-danger" role="alertdialog" aria-labelledby="confirm-delete">
              <p id="confirm-delete" className="mb-2">
                <strong>¿Borrar la cuenta de {displayName(user)}?</strong> No va a poder ingresar y
                se cierran sus sesiones.{' '}
                {user.role === 'company'
                  ? 'El perfil de la empresa y todas sus búsquedas se archivan y salen del matching.'
                  : user.role === 'student'
                    ? 'Su perfil se archiva y sale del matching.'
                    : ''}{' '}
                La cuenta queda guardada para auditoría y{' '}
                {user.company ? 'el email y el CUIT quedan libres' : 'el email queda libre'} para
                una nueva alta.
              </p>
              <div className="d-flex gap-2">
                <button
                  type="button"
                  className="btn btn-sm btn-danger btn-pill"
                  onClick={remove}
                  disabled={busy}
                >
                  {busy && (
                    <span className="spinner-border spinner-border-sm me-1" aria-hidden="true" />
                  )}
                  Sí, borrar la cuenta
                </button>
                <button
                  type="button"
                  className="btn btn-sm btn-outline-secondary btn-pill"
                  onClick={() => setConfirm(null)}
                  disabled={busy}
                >
                  Cancelar
                </button>
              </div>
            </div>
          )}

          {editing ? (
            <form onSubmit={save} noValidate className="row g-3">
              <div className="col-12">
                <TextField
                  label="Email"
                  type="email"
                  required
                  value={form.email}
                  onChange={set('email')}
                  autoComplete="off"
                  hint="Cambia sin confirmación por mail."
                />
                <FieldError message={errors.email} />
              </div>
              {user.role === 'company' && (
                <>
                  <div className="col-12 col-md-6">
                    <TextField
                      label="Razón social"
                      required
                      value={form.legal_name}
                      onChange={set('legal_name')}
                      maxLength={200}
                    />
                    <FieldError message={errors.legal_name} />
                  </div>
                  <div className="col-12 col-md-6">
                    <TextField
                      label="CUIT (sin guiones)"
                      required
                      value={form.cuit}
                      onChange={set('cuit')}
                      maxLength={11}
                    />
                    <FieldError message={errors.cuit} />
                  </div>
                  <div className="col-12">
                    <TextField
                      label="Actividad"
                      required
                      value={form.activity}
                      onChange={set('activity')}
                      maxLength={200}
                    />
                    <FieldError message={errors.activity} />
                  </div>
                </>
              )}
              <div className="col-12 d-flex gap-2">
                <button type="submit" className="btn btn-primary btn-pill" disabled={busy}>
                  {busy && (
                    <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />
                  )}
                  Guardar
                </button>
                <button
                  type="button"
                  className="btn btn-outline-secondary btn-pill"
                  onClick={() => {
                    setEditing(false);
                    setForm(userToForm(user));
                    setErrors({});
                  }}
                  disabled={busy}
                >
                  Cancelar
                </button>
              </div>
            </form>
          ) : (
            <dl className="row g-3 mb-0">
              <Fact label="Email">{user.email}</Fact>
              <Fact label="Email verificado">
                {user.email_verified_at ? dateLabel(user.email_verified_at) : 'No'}
              </Fact>
              {user.company && (
                <>
                  <Fact label="Razón social">{user.company.legal_name}</Fact>
                  <Fact label="CUIT">{user.company.cuit}</Fact>
                  <Fact label="Actividad">{user.company.activity}</Fact>
                </>
              )}
              <Fact label="Alta">{dateLabel(user.created_at)}</Fact>
              <Fact label="Última modificación">{dateLabel(user.updated_at)}</Fact>
              {user.deleted_at && <Fact label="Borrada">{dateLabel(user.deleted_at)}</Fact>}
              <Fact label="ID">
                <code className="small">{user.id}</code>
              </Fact>
            </dl>
          )}
        </div>
      </div>
    </div>
  );
};
