// profile-service · /api/v1/profiles (contracts/profile.md, parte A)
import { ApiError, apiFetch, apiRequest } from './api';
import type {
  CvDesignView,
  CvJob,
  CvLayoutId,
  CvResult,
  ProfileSections,
  ProfileView,
} from '../types/profile';

export type CvFormat = 'pdf' | 'docx';

export const CV_ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.doc', '.md'];
export const CV_MAX_BYTES = 5 * 1024 * 1024;

/** Valida el archivo antes de subirlo (el servicio vuelve a validar MIME y tamaño). */
export function validateCvFile(file: File): string | null {
  const name = file.name.toLowerCase();
  if (!CV_ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext))) {
    return 'Formato no permitido. Usá PDF, DOCX, DOC o MD.';
  }
  if (file.size === 0) return 'El archivo está vacío.';
  if (file.size > CV_MAX_BYTES) return 'El archivo supera el máximo de 5 MB.';
  return null;
}

export const profileService = {
  /** GET /profiles/me · devuelve null si el estudiante todavía no tiene perfil (404). */
  async getMine(): Promise<ProfileView | null> {
    try {
      return await apiFetch<ProfileView>('/profiles/me');
    } catch (err) {
      if (err instanceof ApiError && err.code === 'PROFILE_NOT_FOUND') return null;
      throw err;
    }
  },

  /** POST /profiles/me · alta manual del perfil. */
  create(sections: ProfileSections = {}): Promise<ProfileView> {
    return apiFetch<ProfileView>('/profiles/me', {
      method: 'POST',
      body: JSON.stringify(sections),
    });
  },

  /** PATCH /profiles/me · cada sección enviada se reemplaza completa. */
  update(sections: ProfileSections): Promise<ProfileView> {
    return apiFetch<ProfileView>('/profiles/me', {
      method: 'PATCH',
      body: JSON.stringify(sections),
    });
  },

  /** POST /profiles/me/cv (multipart) → 202 con el trabajo de extracción. */
  uploadCv(file: File): Promise<CvJob> {
    const form = new FormData();
    form.append('file', file);
    return apiFetch<CvJob>('/profiles/me/cv', { method: 'POST', body: form });
  },

  /** GET /profiles/me/cv/jobs/{job_id} · progreso de la extracción. */
  getCvJob(jobId: string): Promise<CvJob> {
    return apiFetch<CvJob>(`/profiles/me/cv/jobs/${encodeURIComponent(jobId)}`);
  },

  /** GET /profiles/me/cv-suggestions · última extracción guardada (o null). */
  async getSuggestions(): Promise<CvResult | null> {
    try {
      return await apiFetch<CvResult>('/profiles/me/cv-suggestions');
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) return null;
      throw err;
    }
  },

  /** DELETE /profiles/me/cv-suggestions · descarta la extracción. */
  discardSuggestions(): Promise<void> {
    return apiFetch<void>('/profiles/me/cv-suggestions', { method: 'DELETE' });
  },

  /** GET /profiles/me/cv-design · diseño que rige, el de reglas, el de IA y el catálogo. */
  getCvDesign(): Promise<CvDesignView> {
    return apiFetch<CvDesignView>('/profiles/me/cv-design');
  },

  /** POST /profiles/me/cv-design/requests · pide a la IA (WF-07) que elija, en segundo plano. */
  requestCvDesign(): Promise<CvDesignView> {
    return apiFetch<CvDesignView>('/profiles/me/cv-design/requests', { method: 'POST' });
  },

  /** PUT /profiles/me/cv-design · elegir un diseño; null vuelve a la elección automática. */
  chooseCvDesign(layout: CvLayoutId | null): Promise<CvDesignView> {
    return apiFetch<CvDesignView>('/profiles/me/cv-design', {
      method: 'PUT',
      body: JSON.stringify({ layout }),
    });
  },

  /** Descarga el CV generado (PDF o Word) usando un blob (la descarga necesita el JWT). */
  async downloadCv(format: CvFormat): Promise<void> {
    const res = await apiRequest(`/profiles/me/cv.${format}`);
    const disposition = res.headers.get('Content-Disposition') ?? '';
    const name = /filename="?([^";]+)"?/.exec(disposition)?.[1] ?? `CV.${format}`;
    const url = URL.createObjectURL(await res.blob());
    const link = Object.assign(document.createElement('a'), { href: url, download: name });
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  },

  /** GET /profiles/me/cv.html · vista previa autocontenida del CV. */
  async previewHtml(): Promise<string> {
    const res = await apiRequest('/profiles/me/cv.html');
    return res.text();
  },
};
