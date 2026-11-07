// matching-service · /api/v1/matches (contracts/matching_frontend.md)
import { apiFetch } from './api';
import type {
  CompanyRecommendationsView,
  RecommendationRequest,
  StudentRecommendationsView,
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

  /** GET /matches/recommendations/requests/{request_id} · estado del pedido. */
  getRequest(requestId: string): Promise<RecommendationRequest> {
    return apiFetch<RecommendationRequest>(
      `/matches/recommendations/requests/${encodeURIComponent(requestId)}`,
    );
  },
};
