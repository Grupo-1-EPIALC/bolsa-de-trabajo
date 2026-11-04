import { 
  Location, 
  WorkConditions, 
  Seniority, 
  ProfileSkillItem, 
  ProfileLanguageItem, 
  EducationItem 
} from './profile';

export type RequirementKind = 'required' | 'desired' | 'excluding';

// Extendemos ProfileSkillItem importado de profile.ts
export interface RequirementSkillItem extends ProfileSkillItem {
  kind: RequirementKind;
}

export interface JobRequirement {
  skills: RequirementSkillItem[];
  languages?: ProfileLanguageItem[];
  education?: EducationItem[];
  experience?: {
    min_years: number;
    area: string;
    kind?: RequirementKind;
  };
  academic?: {
    min_progress_percent?: number;
    careers?: string[];
    min_current_year?: number;
  };
}

export interface JobOpportunity {
  id: string;
  company_id: string;
  title: string;
  description: string;
  status: 'draft' | 'active' | 'paused' | 'closed' | 'expired';
  seniority: Seniority;
  vacancies: number;
  location: Location;
  work_conditions: WorkConditions;
  requirements: JobRequirement;
  benefits?: string[];
  published_at?: string;
  expires_at?: string;
}