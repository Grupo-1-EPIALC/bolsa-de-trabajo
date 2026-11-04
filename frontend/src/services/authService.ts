import { apiFetch } from './api';

export interface LoginPayload {
  email: string;
  password?: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
}

export const authService = {
  // POST /api/v1/auth/token (HU-03)
  login: async (credentials: LoginPayload): Promise<LoginResponse> => {
    const data = await apiFetch<LoginResponse>('/auth/token', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
    localStorage.setItem('access_token', data.access);
    localStorage.setItem('refresh_token', data.refresh);
    return data;
  },

  // POST /api/v1/auth/register (HU-01 / HU-02)
  register: async (payload: any): Promise<void> => {
    return apiFetch<void>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },
};