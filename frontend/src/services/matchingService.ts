import { apiFetch } from './api';
import { MatchResponse } from '../types/matching';

export const matchingService = {
  // GET /api/v1/matching/score?profile_id=...&job_id=... (HU-14)
  getMatchScore: async (profileId: string, jobId: string): Promise<MatchResponse> => {
    return apiFetch<MatchResponse>(`/matching/score?profile_id=${profileId}&job_id=${jobId}`);
  },

  // POST /api/v1/ai/recommendations (HU-15)
  getAIRecommendations: async (profileId: string, jobId: string): Promise<any> => {
    return apiFetch<any>('/ai/recommendations', {
      method: 'POST',
      body: JSON.stringify({ profile_id: profileId, job_id: jobId }),
    });
  },
};