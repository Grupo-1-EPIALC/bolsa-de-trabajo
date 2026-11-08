// Lógica del panel de cuentas (sin React): filtros, formulario de edición y validaciones.
import { ApiError } from '../services/api';
import type { Role } from '../services/session';
import type { AdminUser, AdminUserFilters, AdminUserUpdate } from '../types/admin';
import type { Options } from '../profile/labels';

export const ROLE_LABELS: Options<Role> = [
  ['student', 'Estudiante'],
  ['company', 'Empresa'],
  ['admin', 'Administrador'],
];

export const PAGE_SIZE = 20;

const CUIT_WEIGHTS = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2];

/** Mismo dígito verificador que auth-service (src/auth/cuit.ts). */
export function isValidCuit(cuit: string): boolean {
  if (!/^\d{11}$/.test(cuit)) return false;
  const sum = CUIT_WEIGHTS.reduce((total, weight, i) => total + Number(cuit[i]) * weight, 0);
  const check = 11 - (sum % 11);
  const expected = check === 11 ? 0 : check === 10 ? 9 : check;
  return Number(cuit[10]) === expected;
}

/** Query string de GET /admin/users. Omite los filtros vacíos (un parámetro desconocido da 400). */
export function userListQuery(filters: AdminUserFilters): string {
  const params = new URLSearchParams();
  if (filters.role) params.set('role', filters.role);
  const q = filters.q?.trim();
  if (q) params.set('q', q);
  if (filters.include_deleted) params.set('include_deleted', 'true');
  if (filters.page && filters.page > 1) params.set('page', String(filters.page));
  params.set('size', String(filters.size ?? PAGE_SIZE));
  return `?${params.toString()}`;
}

/** Formulario de edición: email y, para empresas, los datos legales. */
export interface UserForm {
  email: string;
  legal_name: string;
  cuit: string;
  activity: string;
}

export function userToForm(user: AdminUser): UserForm {
  return {
    email: user.email,
    legal_name: user.company?.legal_name ?? '',
    cuit: user.company?.cuit ?? '',
    activity: user.company?.activity ?? '',
  };
}

export type UserFormErrors = Partial<Record<keyof UserForm, string>>;

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateUserForm(form: UserForm, user: AdminUser): UserFormErrors {
  const errors: UserFormErrors = {};
  if (!EMAIL.test(form.email.trim())) errors.email = 'Ingresá un email válido.';
  if (user.role === 'company') {
    if (!form.legal_name.trim()) errors.legal_name = 'La razón social es obligatoria.';
    if (!form.activity.trim()) errors.activity = 'La actividad es obligatoria.';
    if (!isValidCuit(form.cuit)) {
      errors.cuit = /^\d{11}$/.test(form.cuit)
        ? 'El CUIT no es válido (dígito verificador).'
        : 'El CUIT son 11 dígitos, sin guiones.';
    }
  }
  return errors;
}

/** Body del PATCH con sólo lo que cambió. `null` si no hay cambios. */
export function formToUpdate(form: UserForm, user: AdminUser): AdminUserUpdate | null {
  const update: AdminUserUpdate = {};
  const email = form.email.trim().toLowerCase();
  if (email !== user.email.toLowerCase()) update.email = email;
  if (user.role === 'company' && user.company) {
    const company: AdminUserUpdate['company'] = {};
    if (form.legal_name.trim() !== user.company.legal_name) {
      company.legal_name = form.legal_name.trim();
    }
    if (form.cuit !== user.company.cuit) company.cuit = form.cuit;
    if (form.activity.trim() !== user.company.activity) company.activity = form.activity.trim();
    if (Object.keys(company).length) update.company = company;
  }
  return Object.keys(update).length ? update : null;
}

/** Mensaje para cada error del panel; 409 y 404 tienen un texto propio. */
export function adminErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    if (err.status === 409) return 'El email o el CUIT ya están registrados en otra cuenta.';
    if (err.status === 404) return 'La cuenta ya no existe o fue borrada.';
    return err.message;
  }
  return err instanceof Error ? err.message : fallback;
}

/** Qué acciones se ofrecen para una cuenta. El admin no puede borrarse a sí mismo. */
export function userActions(user: AdminUser, currentUserId: string) {
  const self = user.id === currentUserId;
  return {
    edit: !user.deleted,
    resetPassword: !user.deleted,
    remove: !user.deleted && !self,
    self,
  };
}

/** Nombre a mostrar: la razón social para empresas, el email para el resto. */
export function displayName(user: AdminUser): string {
  return user.company?.legal_name || user.email;
}
