// Administración de cuentas · auth-service (contracts/auth_frontend.md §7)
import type { Role } from '../services/session';

export interface AdminCompany {
  legal_name: string;
  cuit: string;
  activity: string;
}

export interface AdminUser {
  id: string;
  email: string;
  role: Role;
  deleted: boolean;
  created_at: string;
  updated_at: string;
  email_verified_at: string | null;
  deleted_at: string | null;
  company?: AdminCompany;
}

export interface AdminUserList {
  items: AdminUser[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface AdminUserFilters {
  role?: Role;
  q?: string;
  include_deleted?: boolean;
  page?: number;
  size?: number;
}

/** Body de PATCH /admin/users/{id}: sólo lo que cambia. */
export interface AdminUserUpdate {
  email?: string;
  company?: Partial<AdminCompany>;
}

export interface PasswordResetResult {
  message: string;
  email_sent: boolean;
}
