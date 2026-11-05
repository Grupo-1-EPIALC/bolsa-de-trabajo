import { apiFetch } from './api';
import { MatchResponse } from '../types/matching';

const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === 'true';

// Mock de fallback local por si se invoca getMatchScore en modo MOCK
const MOCK_MATCH_RESPONSE: MatchResponse = {
  profile_id: 'prof-01',
  job_id: 'job-01',
  rule_based: {
    origin: 'RULES',
    engine_version: '0.1.0',
    score: 82.5,
    excluding_cap_applied: false,
    breakdown: {
      required_skills: 45,
      desired_skills: 15,
      skill_levels: 12.5,
      experience: 5,
      education: 5,
      languages: 0,
    },
    missing_skills: [
      { skill: 'TypeScript', required_level: 2, current_level: 0, gap: 2, priority: 'alta', kind: 'required' },
      { skill: 'Docker', required_level: 2, current_level: 0, gap: 2, priority: 'media', kind: 'desired' },
    ],
  },
  ai_recommendations: {
    origin: 'AI',
    model: 'nvidia/llama-3.1-70b-instruct',
    generated_at: '2026-11-04T10:00:00Z',
    prompt_version: '1.0.0',
    disclaimer: 'Sugerencia generada por IA orientativa. Los puntajes oficiales se basan strictly en las reglas del sistema.',
    items: [
      { type: 'course', skill: 'TypeScript', text: 'Realizar un taller práctico de TypeScript enfocado en React SPA para elevar nivel 0 a 2.', priority: 'alta' },
      { type: 'profile_improvement', text: 'Subir al perfil proyectos personales que utilicen Docker compose local.', priority: 'media' },
    ],
  },
};

export const matchingService = {
  // GET /api/v1/matching/score?profile_id=...&job_id=...
  getMatchScore: async (profileId: string, jobId: string): Promise<MatchResponse> => {
    if (USE_MOCKS) {
      return Promise.resolve(MOCK_MATCH_RESPONSE);
    }
    return apiFetch<MatchResponse>(`/matching/score?profile_id=${profileId}&job_id=${jobId}`);
  },

  // POST /api/v1/ai/recommendations
  getAIRecommendations: async (profileId: string, jobId: string): Promise<any> => {
    if (USE_MOCKS) {
      return Promise.resolve(MOCK_MATCH_RESPONSE.ai_recommendations);
    }
    return apiFetch<any>('/ai/recommendations', {
      method: 'POST',
      body: JSON.stringify({ profile_id: profileId, job_id: jobId }),
    });
  },
};