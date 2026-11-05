// src/services/matchingService.ts
import { apiFetch } from './api';
import {
  MatchResponse,
  StudentRecommendationItem,
  JobCandidateRecommendationItem,
} from '../types/matching';

const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === 'true';

// Mock de prueba alineado con los IDs del pool de demo del backend (stu-001 / job-001)
const MOCK_MATCH_RESPONSE: MatchResponse = {
  profile_id: 'stu-001',
  job_id: 'job-001',
  rule_based: {
    origin: 'RULES',
    engine_version: '1.0.0',
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
      {
        skill: 'TypeScript',
        required_level: 2,
        current_level: 0,
        gap: 2,
        priority: 'alta',
        kind: 'required',
      },
      {
        skill: 'Docker',
        required_level: 2,
        current_level: 0,
        gap: 2,
        priority: 'media',
        kind: 'desired',
      },
    ],
    conditions_fit: {
      salary_fit: true,
      modality_fit: true,
    },
  },
  ai_recommendations: {
    origin: 'AI',
    model: 'nvidia/llama-3.1-70b-instruct',
    generated_at: '2026-11-04T10:00:00Z',
    prompt_version: '1.0.0',
    disclaimer:
      'Sugerencia generada por IA orientativa. Los puntajes oficiales se basan estrictamente en las reglas del sistema.',
    items: [
      {
        type: 'course',
        skill: 'TypeScript',
        text: 'Realizar un taller práctico de TypeScript enfocado en React SPA para elevar nivel 0 a 2.',
        priority: 'alta',
      },
      {
        type: 'profile_improvement',
        text: 'Subir al perfil proyectos personales que utilicen Docker compose local.',
        priority: 'media',
      },
    ],
  },
};

export const matchingService = {
  // Evaluar o consultar el score puntual entre un candidato y una búsqueda
  // POST /api/v1/matches (o GET /api/v1/matching/score como alias)
  getMatchScore: async (
    profileId: string = 'stu-001',
    jobId: string = 'job-001',
  ): Promise<MatchResponse> => {
    if (USE_MOCKS) {
      return Promise.resolve(MOCK_MATCH_RESPONSE);
    }
    return apiFetch<MatchResponse>('/matches', {
      method: 'POST',
      body: JSON.stringify({ profile_id: profileId, job_id: jobId }),
    });
  },

  // Obtener ofertas recomendadas para un estudiante (Vista Estudiante)
  // GET /api/v1/matches/recommendations/students/{profile_id}?limit=5
  getStudentRecommendations: async (
    profileId: string = 'stu-001',
    limit: number = 5,
  ): Promise<StudentRecommendationItem[]> => {
    if (USE_MOCKS) {
      return Promise.resolve([
        {
          job_id: 'job-001',
          job_title: 'Desarrollador Frontend Trainee',
          company_name: 'TechSolutions UTN',
          score: 82.5,
          match: MOCK_MATCH_RESPONSE,
        },
      ]);
    }
    return apiFetch<StudentRecommendationItem[]>(
      `/matches/recommendations/students/${profileId}?limit=${limit}`,
    );
  },

  // Obtener candidatos recomendados para una oferta (Vista Empresa)
  // GET /api/v1/matches/recommendations/jobs/{job_id}?limit=10
  getJobCandidates: async (
    jobId: string = 'job-001',
    limit: number = 10,
  ): Promise<JobCandidateRecommendationItem[]> => {
    if (USE_MOCKS) {
      return Promise.resolve([
        {
          profile_id: 'stu-001',
          candidate_name: 'Lucía Pérez',
          score: 82.5,
          match: MOCK_MATCH_RESPONSE,
        },
      ]);
    }
    return apiFetch<JobCandidateRecommendationItem[]>(
      `/matches/recommendations/jobs/${jobId}?limit=${limit}`,
    );
  },

  // Solicitar recálculo o recomendaciones asíncronas por IA
  // POST /api/v1/matches/recommendations/requests
  requestAIRecommendations: async (
    profileId: string = 'stu-001',
    jobId: string = 'job-001',
  ): Promise<any> => {
    if (USE_MOCKS) {
      return Promise.resolve(MOCK_MATCH_RESPONSE.ai_recommendations);
    }
    return apiFetch<any>('/matches/recommendations/requests', {
      method: 'POST',
      body: JSON.stringify({ profile_id: profileId, job_id: jobId }),
    });
  },
};
