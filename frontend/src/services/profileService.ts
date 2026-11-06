import { apiFetch } from './api';
import { MOCK_STUDENT_PROFILE } from './mockData';
import { StudentProfile } from '../types/profile';

const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === 'true';

export const profileService = {
  // GET /api/v1/profiles/me
  getProfile: async (): Promise<StudentProfile> => {
    if (USE_MOCKS) {
      return Promise.resolve(MOCK_STUDENT_PROFILE);
    }
    return apiFetch<StudentProfile>('/profiles/me');
  },

  // PUT /api/v1/profiles/me
  updateProfile: async (profile: Partial<StudentProfile>): Promise<StudentProfile> => {
    if (USE_MOCKS) {
      console.log('[MOCK] Actualizando perfil:', profile);
      return Promise.resolve({ ...MOCK_STUDENT_PROFILE, ...profile });
    }
    return apiFetch<StudentProfile>('/profiles/me', {
      method: 'PUT',
      body: JSON.stringify(profile),
    });
  },

  // POST /api/v1/profiles/me/cv
  uploadCV: async (file: File): Promise<{ message: string; filename: string }> => {
    if (USE_MOCKS) {
      console.log('[MOCK] Simulando subida de CV:', file.name);
      return Promise.resolve({
        message: 'CV subido y simulado exitosamente (MODO MOCK)',
        filename: file.name,
      });
    }

    const formData = new FormData();
    formData.append('file', file);

    const token = localStorage.getItem('access_token');
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080/api/v1';

    const response = await fetch(`${baseUrl}/profiles/me/cv`, {
      method: 'POST',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: formData,
    });

    if (!response.ok) {
      throw new Error('Error al subir el archivo de CV al servidor');
    }

    return response.json();
  },
};
