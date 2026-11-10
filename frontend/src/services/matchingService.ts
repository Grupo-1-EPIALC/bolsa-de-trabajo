// matching-service · /api/v1/matches (contracts/matching.md, parte A)
import { apiFetch } from './api';
import type {
  CompanyRecommendationsView,
  RecommendationRequest,
  RecommendationSettings,
  RecommendationSettingsUpdate,
  StudentRecommendationsView,
  TrainingView,
} from '../types/matching';

export const matchingService = {
  /** GET /matches/recommendations/students/{profile_id} · ofertas para el estudiante. */
  getStudentRecommendations(profileId: string): Promise<StudentRecommendationsView> {
    return apiFetch<StudentRecommendationsView>(
      `/matches/recommendations/students/${encodeURIComponent(profileId)}`,
    );
  },

  /** POST /matches/recommendations/requests · pide el análisis con IA (WF-06). */
  requestStudentAnalysis(profileId: string): Promise<RecommendationRequest> {
    return apiFetch<RecommendationRequest>('/matches/recommendations/requests', {
      method: 'POST',
      body: JSON.stringify({ mode: 'student', profile_id: profileId }),
    });
  },

  /** GET /matches/recommendations/jobs/{job_id} · candidatos por reglas para una búsqueda propia. */
  getCompanyRecommendations(jobId: string): Promise<CompanyRecommendationsView> {
    return apiFetch<CompanyRecommendationsView>(
      `/matches/recommendations/jobs/${encodeURIComponent(jobId)}`,
    );
  },

  /** POST /matches/recommendations/requests · análisis con IA de los candidatos (WF-06). */
  requestCompanyAnalysis(jobId: string): Promise<RecommendationRequest> {
    return apiFetch<RecommendationRequest>('/matches/recommendations/requests', {
      method: 'POST',
      body: JSON.stringify({ mode: 'company', job_id: jobId }),
    });
  },

  /** GET /matches/recommendations/students/{id}/training · qué sumar o mejorar, en general. */
  getTraining(profileId: string): Promise<TrainingView> {
    return apiFetch<TrainingView>(
      `/matches/recommendations/students/${encodeURIComponent(profileId)}/training`,
    );
  },

  /** POST /matches/recommendations/requests · pide la formación general a la IA (mode=training). */
  requestTraining(profileId: string): Promise<RecommendationRequest> {
    return apiFetch<RecommendationRequest>('/matches/recommendations/requests', {
      method: 'POST',
      body: JSON.stringify({ mode: 'training', profile_id: profileId }),
    });
  },

  /** GET /matches/settings · cuántas ofertas y candidatos se recomiendan (sólo admin). */
  getSettings(): Promise<RecommendationSettings> {
    return apiFetch<RecommendationSettings>('/matches/settings');
  },

  /** PATCH /matches/settings · sólo los campos que cambian. */
  updateSettings(changes: RecommendationSettingsUpdate): Promise<RecommendationSettings> {
    return apiFetch<RecommendationSettings>('/matches/settings', {
      method: 'PATCH',
      body: JSON.stringify(changes),
    });
  },

  /** GET /matches/recommendations/requests/{request_id} · estado del pedido. */
  getRequest(requestId: string): Promise<RecommendationRequest> {
    return apiFetch<RecommendationRequest>(
      `/matches/recommendations/requests/${encodeURIComponent(requestId)}`,
    );
  },
};
