// auth-service (NestJS) · /api/v1/auth
import { apiFetch } from './api';
import { session, SessionUser, TokenPair } from './session';

export interface LoginPayload {
  email: string;
  password: string;
}

export interface CompanyData {
  legal_name: string;
  cuit: string;
  activity: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  role: 'student' | 'company';
  company?: CompanyData;
}

type AuthResponse = TokenPair & { user: SessionUser };

export const PASSWORD_MIN_LENGTH = 12;

export const authService = {
  /** POST /auth/token → inicia la sesión. */
  async login(credentials: LoginPayload): Promise<SessionUser> {
    const data = await apiFetch<AuthResponse>('/auth/token', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
    session.start(data.user, data);
    return data.user;
  },

  /** POST /auth/register → crea la cuenta e inicia la sesión (auth-service devuelve los tokens). */
  async register(payload: RegisterPayload): Promise<SessionUser> {
    const data = await apiFetch<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    session.start(data.user, data);
    return data.user;
  },

  /** POST /auth/password/reset → Solicita el enlace de recuperación por email. */
  async requestPasswordReset(email: string): Promise<void> {
    await apiFetch('/auth/password/reset', {
      method: 'POST',
      body: JSON.stringify({ email }),
    });
  },

  /** POST /auth/password/reset/confirm → Establece la nueva contraseña usando el token. */
  async confirmPasswordReset(token: string, new_password: string): Promise<void> {
    await apiFetch('/auth/password/reset/confirm', {
      method: 'POST',
      body: JSON.stringify({ token, new_password }),
    });
  },

  /** POST /auth/email/confirm → Confirma la nueva dirección de email usando el token recibido. */
  async confirmEmail(token: string): Promise<void> {
    await apiFetch<void>('/auth/email/confirm', {
      method: 'POST',
      body: JSON.stringify({ token }),
    });
  },

  /** GET /auth/me → Obtiene los datos de la cuenta activa (email y rol). */
  async me(): Promise<SessionUser> {
    return apiFetch<SessionUser>('/auth/me');
  },

  /** POST /auth/password/change → Cambia la contraseña actual por una nueva. Cierra las sesiones activas. */
  async changePassword(current_password: string, new_password: string): Promise<void> {
    await apiFetch<void>('/auth/password/change', {
      method: 'POST',
      body: JSON.stringify({ current_password, new_password }),
    });
  },

  /** POST /auth/email/change → Solicita cambiar la dirección de correo (dispara email con token). */
  async requestEmailChange(email: string, current_password: string): Promise<void> {
    await apiFetch<void>('/auth/email/change', {
      method: 'POST',
      body: JSON.stringify({ email, current_password }),
    });
  },

  logout() {
    session.clear();
  },
};
