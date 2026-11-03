// Contrato estricto del TP2 para Scoring por Reglas (Determinístico)
export interface MissingSkill {
  skill: string;
  required_level: number;
  current_level: number;
}

export interface RuleBasedResult {
  origin: 'RULES';
  engine_version: string;
  score: number;
  breakdown: {
    required_skills: number;
    desired_skills: number;
    levels: number;
    experience: number;
    education: number;
    languages: number;
  };
  missing_skills: MissingSkill[];
}

// Contrato estricto del TP2 para Recomendaciones por IA (Orientativo)
export interface AIRecommendationItem {
  type: string;
  skill: string;
  text: string;
  priority: 'alta' | 'media' | 'baja';
}

export interface AIRecommendationResult {
  origin: 'AI';
  model: string;
  generated_at: string;
  disclaimer: string;
  items: AIRecommendationItem[];
}

// Respuesta combinada que entrega la API o el Gateway
export interface MatchResponse {
  profile_id?: number;
  job_id?: number;
  rule_based: RuleBasedResult;
  ai_recommendations: AIRecommendationResult;
}