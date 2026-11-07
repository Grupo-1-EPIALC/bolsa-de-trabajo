// Tipos de matching-service según contracts/matching_frontend.md (§4).
// El score y el orden salen siempre de rule_based (origin RULES); la IA nunca trae score.

import type { ApiErrorBody, Location, WorkConditions } from './profile';

export type Priority = 'alta' | 'media' | 'baja';
export type ConditionResult = 'match' | 'partial' | 'mismatch' | 'unknown' | string;

export interface BreakdownItem {
  criterion: string;
  weight: number;
  earned: number;
  details?: Record<string, unknown>;
}

export interface MatchedSkill {
  skill: string;
  kind: string;
  profile_level: number;
  required_level: number;
}

export interface MissingSkill {
  skill: string;
  kind: string;
  required_level: number;
  current_level: number;
  gap: number;
  priority: Priority;
}

export interface ConditionCheck {
  condition: string;
  result: ConditionResult;
  hard: boolean;
  profile_value?: unknown;
  job_value?: unknown;
}

export interface SalaryFit {
  result: ConditionResult;
  expected_monthly?: { min: number; max: number } | null;
  offered_monthly?: { min: number; max: number } | null;
  gap_percent?: number | null;
  currency?: string;
}

/** Match por reglas (§4.4). */
export interface Match {
  origin: 'RULES';
  engine_version: string;
  rules_version?: string;
  computed_at?: string;
  profile_id: string;
  job_id: string;
  score: number;
  excluding_cap_applied: boolean;
  breakdown: BreakdownItem[];
  matched_skills: MatchedSkill[];
  missing_skills: MissingSkill[];
  conditions_fit?: {
    compatible: boolean;
    distance_km?: number | null;
    checks: ConditionCheck[];
    salary_fit?: SalaryFit;
  };
}

export interface JobSnapshot {
  job_id: string;
  title: string;
  company_name?: string;
  seniority?: string;
  location?: Partial<Location>;
  work_conditions?: WorkConditions;
  [extra: string]: unknown;
}

export interface StudentRuleItem {
  rank: number;
  job: JobSnapshot;
  match: Match;
}

export interface NextStep {
  type: string;
  skill?: string;
  text: string;
  priority?: Priority;
}

export interface StudentAIItem {
  job_id: string;
  content: {
    priority?: Priority;
    fit_reasons?: string[];
    watch_outs?: string[];
    next_steps?: NextStep[];
  };
}

export type AIStatus =
  'not_requested' | 'pending' | 'processing' | 'ready' | 'completed' | 'failed';

/** Bloque de IA (origin AI): nunca trae score; `items` se une por id con el bloque por reglas. */
export interface AIBlock<T> {
  origin: 'AI';
  status: AIStatus;
  request_id?: string | null;
  error?: ApiErrorBody | null;
  summary?: string;
  model?: string;
  prompt_version?: string;
  generated_at?: string;
  disclaimer?: string;
  verified?: boolean;
  items?: T[];
}

/** Vista del estudiante (§4.1). */
export interface StudentRecommendationsView {
  profile_id: string;
  rule_based: {
    origin: 'RULES';
    engine_version: string;
    rules_version?: string;
    evaluated: number;
    excluded_incompatible: number;
    items: StudentRuleItem[];
  };
  ai_recommendations: AIBlock<StudentAIItem>;
}

/** Candidato anonimizado (§4.2): sin nombre, email, teléfono ni dirección. */
export interface CandidateSnapshot {
  profile_id: string;
  headline?: string | null;
  location?: Partial<Location> | null;
  years_experience?: number | null;
  skills?: Array<{ name: string; level: number }>;
  languages?: Array<{ name: string; level: string }>;
  education?: Array<{
    level: string;
    status: string;
    degree?: string | null;
    field?: string | null;
  }>;
  academic_status?: {
    career?: string | null;
    current_year?: number | null;
    progress_percent?: number | null;
  } | null;
  target_roles?: string[];
  work_conditions?: WorkConditions;
  [extra: string]: unknown;
}

export interface CompanyRuleItem {
  rank: number;
  candidate: CandidateSnapshot;
  match: Match;
}

export interface CompanyAIItem {
  profile_id: string;
  content: {
    priority?: Priority;
    justification?: string;
    strengths?: string[];
    gaps?: string[];
    conditions_alerts?: string[];
    interview_questions?: string[];
  };
}

/** Vista de la empresa (§4.2): candidatos para una búsqueda propia. */
export interface CompanyRecommendationsView {
  job_id: string;
  rule_based: {
    origin: 'RULES';
    engine_version: string;
    rules_version?: string;
    job_id: string;
    job?: JobSnapshot;
    evaluated: number;
    excluded_incompatible: number;
    items: CompanyRuleItem[];
  };
  ai_recommendations: AIBlock<CompanyAIItem>;
}

/** Pedido de análisis con IA (§4.3). */
export interface RecommendationRequest {
  request_id: string;
  mode: 'student' | 'company';
  subject_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
  limit?: number;
  error: ApiErrorBody | null;
}
