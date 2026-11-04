import { apiFetch } from './api';
import { StudentProfile } from '../types/profile';

export const profileService = {
  // GET /api/v1/profiles/me (HU-07)
  getProfile: async (): Promise<StudentProfile> => {
    return apiFetch<StudentProfile>('/profiles/me');
  },

  // PUT /api/v1/profiles/me (HU-07)
  updateProfile: async (profile: Partial<StudentProfile>): Promise<StudentProfile> => {
    return apiFetch<StudentProfile>('/profiles/me', {
      method: 'PUT',
      body: JSON.stringify(profile),
    });
  },

  // POST /api/v1/profiles/me/cv (HU-08)
  uploadCV: async (file: File): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);

    const token = localStorage.getItem('access_token');
    const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080/api/v1'}/profiles/me/cv`, {
      method: 'POST',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: formData,
    });

    if (!response.ok) {
      throw new Error('Error al subir el archivo de CV');
    }

    return response.json();
  },
};