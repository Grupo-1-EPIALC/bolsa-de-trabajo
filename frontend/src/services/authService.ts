import { apiFetch } from './api';

export interface LoginPayload {
  email: string;
  password?: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
}

const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === 'true';

export const authService = {
  // POST /api/v1/auth/token
  login: async (credentials: LoginPayload): Promise<LoginResponse> => {
    if (USE_MOCKS) {
      console.log('[MOCK] Login simulado para:', credentials.email);
      const fakeTokens = {
        access: 'mock_jwt_access_token_xyz_123',
        refresh: 'mock_jwt_refresh_token_xyz_123',
      };
      localStorage.setItem('access_token', fakeTokens.access);
      localStorage.setItem('refresh_token', fakeTokens.refresh);
      return Promise.resolve(fakeTokens);
    }

    const data = await apiFetch<LoginResponse>('/auth/token', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
    localStorage.setItem('access_token', data.access);
    localStorage.setItem('refresh_token', data.refresh);
    return data;
  },

  // POST /api/v1/auth/register
  register: async (payload: any): Promise<void> => {
    if (USE_MOCKS) {
      console.log('[MOCK] Registro simulado:', payload);
      return Promise.resolve();
    }

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
