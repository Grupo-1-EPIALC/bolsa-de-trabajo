// src/types/matching.ts
// Tipos oficiales alineados con matching-service v0.1.0 (contrato OpenAPI / matching_frontend.md)

export type MissingSkillKind = 'required' | 'desired';
export type SkillPriority = 'alta' | 'media' | 'baja';

export interface MissingSkill {
  skill: string;
  required_level: number;
  current_level: number;
  gap: number;
  priority: SkillPriority;
  kind: MissingSkillKind;
}

export interface ScoreBreakdown {
  required_skills: number;
  desired_skills: number;
  skill_levels: number;
  experience: number;
  education: number;
  languages: number;
}

export interface ConditionsFit {
  salary_fit?: boolean;
  modality_fit?: boolean;
  location_distance_km?: number;
}

// Bloque determinístico de Reglas (origin: "RULES")
export interface RuleBasedResult {
  origin: 'RULES';
  engine_version: string;
  score: number;
  excluding_cap_applied?: boolean;
  breakdown: ScoreBreakdown;
  missing_skills: MissingSkill[];
  conditions_fit?: ConditionsFit;
}

export interface AIRecommendationItem {
  type: 'course' | 'profile_improvement' | 'cert' | string;
  skill?: string;
  text: string;
  priority: SkillPriority;
}

// Bloque orientativo de IA (origin: "AI")
export interface AIRecommendationResult {
  origin: 'AI';
  model: string;
  generated_at: string;
  prompt_version?: string;
  disclaimer: string;
  items: AIRecommendationItem[];
}

// Respuesta completa de evaluación (POST /api/v1/matches)
export interface MatchResponse {
  profile_id: string;
  job_id: string;
  rule_based: RuleBasedResult;
  ai_recommendations: AIRecommendationResult;
}

// Recomendaciones para candidatos (GET /api/v1/matches/recommendations/students/{profile_id})
export interface StudentRecommendationItem {
  job_id: string;
  job_title: string;
  company_name?: string;
  score: number;
  match: MatchResponse;
}

// Recomendaciones para empresas (GET /api/v1/matches/recommendations/jobs/{job_id})
export interface JobCandidateRecommendationItem {
  profile_id: string;
  candidate_name?: string;
  score: number;
  match: MatchResponse;
}