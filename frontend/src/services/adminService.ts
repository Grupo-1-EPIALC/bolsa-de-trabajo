// auth-service · /api/v1/auth/admin/users (contracts/auth_frontend.md §7) · sólo rol admin.
import { apiFetch } from './api';
import { userListQuery } from '../admin/users';
import type {
  AdminUser,
  AdminUserFilters,
  AdminUserList,
  AdminUserUpdate,
  PasswordResetResult,
} from '../types/admin';

const base = '/auth/admin/users';
const one = (id: string) => `${base}/${encodeURIComponent(id)}`;

export const adminService = {
  /** GET /admin/users · listado con filtros, más nuevas primero. */
  list(filters: AdminUserFilters): Promise<AdminUserList> {
    return apiFetch<AdminUserList>(`${base}${userListQuery(filters)}`);
  },

  /** GET /admin/users/{id} · también trae las cuentas borradas. */
  get(id: string): Promise<AdminUser> {
    return apiFetch<AdminUser>(one(id));
  },

  /** PATCH /admin/users/{id} · email y/o datos de empresa. 409 si el email o el CUIT ya existen. */
  update(id: string, changes: AdminUserUpdate): Promise<AdminUser> {
    return apiFetch<AdminUser>(one(id), { method: 'PATCH', body: JSON.stringify(changes) });
  },

  /** POST /admin/users/{id}/password-reset · invalida la clave y manda el link de recuperación. */
  resetPassword(id: string): Promise<PasswordResetResult> {
    return apiFetch<PasswordResetResult>(`${one(id)}/password-reset`, { method: 'POST' });
  },

  /** DELETE /admin/users/{id} · borrado lógico (204). */
  remove(id: string): Promise<void> {
    return apiFetch<void>(one(id), { method: 'DELETE' });
  },
};
