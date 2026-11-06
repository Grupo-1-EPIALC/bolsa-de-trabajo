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

  logout() {
    session.clear();
  },
};
