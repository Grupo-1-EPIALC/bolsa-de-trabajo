// Perfil de empresa (profile-service, /api/v1/profiles/companies). Las búsquedas van en jobsService.
import { ApiError, apiFetch } from './api';
import type { CompanyProfile, CompanySections } from '../types/company';

export const LOGO_MAX_BYTES = 1024 * 1024;
const LOGO_TYPES = ['image/png', 'image/jpeg', 'image/webp'];

/** Validación previa del logo (el servicio vuelve a validar por contenido). */
export function validateLogo(file: File): string | null {
  if (!LOGO_TYPES.includes(file.type)) return 'El logo tiene que ser PNG, JPEG o WebP.';
  if (file.size === 0) return 'El archivo está vacío.';
  if (file.size > LOGO_MAX_BYTES) return 'El logo supera el máximo de 1 MB.';
  return null;
}

export const companyService = {
  /** GET /profiles/companies/me · null si la empresa todavía no tiene perfil. */
  async getMine(): Promise<CompanyProfile | null> {
    try {
      return await apiFetch<CompanyProfile>('/profiles/companies/me');
    } catch (err) {
      if (err instanceof ApiError && err.code === 'COMPANY_PROFILE_NOT_FOUND') return null;
      throw err;
    }
  },

  /**
   * GET /profiles/companies/{company_id}
   * Devuelve el perfil público de la empresa para ser consultado desde las ofertas de empleo.
   */
  getPublicProfile(companyId: string): Promise<CompanyProfile> {
    return apiFetch<CompanyProfile>(`/profiles/companies/${encodeURIComponent(companyId)}`);
  },

  /** POST /profiles/companies/me · se precarga con razón social, actividad y email. */
  create(sections: CompanySections = {}): Promise<CompanyProfile> {
    return apiFetch<CompanyProfile>('/profiles/companies/me', {
      method: 'POST',
      body: JSON.stringify(sections),
    });
  },

  /** PATCH /profiles/companies/me · cada sección enviada se reemplaza entera. */
  update(sections: CompanySections): Promise<CompanyProfile> {
    return apiFetch<CompanyProfile>('/profiles/companies/me', {
      method: 'PATCH',
      body: JSON.stringify(sections),
    });
  },

  /** PUT /profiles/companies/me/logo (multipart, campo file). */
  uploadLogo(file: File): Promise<CompanyProfile> {
    const form = new FormData();
    form.append('file', file);
    return apiFetch<CompanyProfile>('/profiles/companies/me/logo', { method: 'PUT', body: form });
  },

  /** DELETE /profiles/companies/me/logo. */
  deleteLogo(): Promise<void> {
    return apiFetch<void>('/profiles/companies/me/logo', { method: 'DELETE' });
  },
};
