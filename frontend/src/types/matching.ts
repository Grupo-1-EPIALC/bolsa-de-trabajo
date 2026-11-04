export type Priority = 'alta' | 'media' | 'baja';
export type RequirementKind = 'required' | 'desired' | 'excluding';

export interface Breakdown {
  required_skills: number;
  desired_skills: number;
  skill_levels: number;
  experience: number;
  education: number;
  languages: number;
}

export interface MissingSkill {
  skill: string;
  required_level: number;
  current_level: number;
  gap: number;
  priority: Priority;
  kind?: RequirementKind;
}

export interface RuleBasedResult {
  origin: 'RULES';
  engine_version: string;
  score: number;
  excluding_cap_applied: boolean;
  breakdown: Breakdown;
  missing_skills: MissingSkill[];
}

export interface AIRecommendationItem {
  type: string;
  skill?: string;
  text: string;
  priority: Priority;
}

export interface AIRecommendations {
  origin: 'AI';
  model: string;
  generated_at: string;
  prompt_version?: string;
  disclaimer: string;
  items: AIRecommendationItem[];
}

export interface MatchResponse {
  profile_id: string;
  job_id: string;
  rule_based: RuleBasedResult;
  ai_recommendations: AIRecommendations;
}