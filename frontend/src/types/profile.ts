// Enums compartidos del TP2 (Estructura de datos común §3)
export type WorkSchedule = 'full_time' | 'part_time' | 'hourly' | 'flexible';
export type WorkModality = 'onsite' | 'remote' | 'hybrid';
export type EmploymentType = 'employee' | 'freelance' | 'internship' | 'trainee';
export type ContractDuration = 'permanent' | 'fixed_term' | 'project' | 'seasonal';
export type AvailabilityStart = 'immediate' | 'within_15_days' | 'within_30_days' | 'to_agree';
export type Shift = 'morning' | 'afternoon' | 'evening' | 'night' | 'weekend' | 'rotating';
export type Seniority = 'no_experience' | 'trainee' | 'junior' | 'semi_senior' | 'senior';
export type LanguageLevel = 'A1' | 'A2' | 'B1' | 'B2' | 'C1' | 'C2' | 'native';
export type EducationLevel = 'secondary' | 'tertiary' | 'university' | 'postgraduate' | 'course';
export type EducationStatus = 'in_progress' | 'completed' | 'incomplete';
export type Currency = 'ARS' | 'USD';
export type SalaryPeriod = 'hour' | 'day' | 'month' | 'year' | 'project';
export type SalaryVisibility = 'public' | 'on_match' | 'hidden';
export type ProfileVisibility = 'public_to_companies' | 'only_applied' | 'hidden';
export type JobSearchStatus = 'active' | 'open_to_offers' | 'not_looking';

// Bloques reutilizables (§4)
export interface Location {
  country: string; // ISO-3166 alfa 2 (ej. "AR")
  province: string;
  city: string;
  postal_code?: string;
  zone?: string;
}

export interface SalaryRange {
  min?: number;
  max?: number;
  currency?: Currency;
  period?: SalaryPeriod;
  gross?: boolean;
  visibility?: SalaryVisibility;
  to_agree?: boolean;
}

export interface WorkConditions {
  work_schedule?: WorkSchedule[];
  work_modality?: WorkModality[];
  hybrid_onsite_days?: number;
  employment_type?: EmploymentType[];
  contract_duration?: ContractDuration[];
  shifts?: Shift[];
  availability_start?: AvailabilityStart;
  salary?: SalaryRange;
  willing_to_relocate?: boolean;
  max_commute_km?: number;
}

export interface ProfileSkillItem {
  name: string;
  normalized: string;
  level: number; // 1 to 5
  years?: number;
  category?: 'hard' | 'soft' | 'tool' | 'methodology';
  source?: 'cv_ai' | 'manual';
  confirmed?: boolean;
}

export interface ProfileLanguageItem {
  name: string;
  normalized: string;
  level: LanguageLevel;
  certification?: string;
}

export interface EducationItem {
  institution: string;
  degree: string;
  field?: string;
  level: EducationLevel;
  status: EducationStatus;
  start?: string; // YYYY-MM
  end?: string; // YYYY-MM
  progress_percent?: number;
}

export interface ExperienceItem {
  company: string;
  role: string;
  start: string;
  end: string; // "actual" o YYYY-MM
  description?: string;
  area?: string;
  employment_type?: EmploymentType;
  work_modality?: WorkModality;
  skills_used?: string[];
}

export interface ProjectItem {
  name: string;
  description: string;
  url?: string;
  skills_used?: string[];
}

// Entidad principal: StudentProfile (§5)
export interface StudentProfile {
  id: string;
  user_id: string;
  personal: {
    name: string;
    email: string;
    phone: string;
    birth_year?: number;
    location: Location;
  };
  summary?: string;
  headline?: string;
  academic_status: {
    institution: string;
    career: string;
    current_year?: number;
    progress_percent?: number;
    expected_graduation?: string;
    student_shift?: Shift[];
  };
  target?: {
    roles: string[];
    areas: string[];
    seniority: Seniority;
  };
  work_conditions?: WorkConditions;
  skills: ProfileSkillItem[];
  experience: ExperienceItem[];
  education: EducationItem[];
  languages: ProfileLanguageItem[];
  projects?: ProjectItem[];
  visibility: ProfileVisibility;
  job_search_status: JobSearchStatus;
  cv_files?: Array<{
    stored_filename: string;
    mime_type: string;
    uploaded_at: string;
  }>;
}
