// Tipos del perfil del estudiante según contracts/profile_frontend.md (profile-service v0.2.0)
// y la estructura común §3–§5. Los opcionales sin valor no vienen en el JSON (no hay null).

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
export type SkillCategory = 'hard' | 'soft' | 'tool' | 'methodology';
export type LinkType = 'linkedin' | 'github' | 'portfolio' | 'other';
export type ProfileStep = 'cv' | 'preferences' | 'privacy';

export interface Location {
  country: string; // ISO-3166 alfa-2 (ej. "AR")
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
  negotiable?: boolean;
  visibility?: SalaryVisibility;
  to_agree?: boolean;
}

export interface WorkConditions {
  work_schedule?: WorkSchedule[];
  work_modality?: WorkModality[];
  hybrid_onsite_days?: number;
  employment_type?: EmploymentType[];
  contract_duration?: ContractDuration[];
  weekly_hours?: { min?: number; max?: number };
  shifts?: Shift[];
  availability_start?: AvailabilityStart;
  salary?: SalaryRange;
  willing_to_relocate?: boolean;
  max_commute_km?: number;
  [extra: string]: unknown; // campos que el front no edita se conservan tal cual
}

export interface Personal {
  name: string;
  email: string;
  phone?: string;
  birth_year?: number;
  location?: Location;
}

export interface AcademicStatus {
  institution?: string;
  career?: string;
  current_year?: number;
  progress_percent?: number;
  expected_graduation?: string;
  student_shift?: Shift[];
}

export interface Target {
  roles?: string[];
  areas?: string[];
  seniority?: Seniority;
}

export interface SkillItem {
  name: string;
  normalized?: string; // lo calcula el servicio
  level: number; // 1 a 5
  years?: number;
  category?: SkillCategory;
  source?: 'cv_ai' | 'manual';
  confirmed?: boolean;
}

export interface LanguageItem {
  name: string;
  normalized?: string;
  level: LanguageLevel;
  certification?: string;
}

export interface EducationItem {
  institution: string;
  degree: string;
  field?: string;
  level: EducationLevel;
  status: EducationStatus;
  start?: string;
  end?: string;
  progress_percent?: number;
}

export interface ExperienceItem {
  company: string;
  role: string;
  start: string;
  end?: string; // "actual" o YYYY-MM
  description?: string;
  skills_used?: string[];
  months?: number; // lo calcula el servicio
  [extra: string]: unknown;
}

/** Alias usados por types/jobs.ts (jobs-service). */
export type ProfileSkillItem = SkillItem;
export type ProfileLanguageItem = LanguageItem;

export interface CertificationItem {
  name: string;
  issuer?: string;
  year?: number;
  url?: string;
}

export interface LinkItem {
  type: LinkType;
  url: string;
}

export interface Consents {
  data_processing: boolean;
  ai_processing: boolean;
  contact_by_email: boolean;
  accepted_at?: string;
}

export interface CompletionStep {
  step: ProfileStep;
  complete: boolean;
  missing_required: number;
  missing_recommended: number;
}

export interface MissingField {
  field: string;
  step: ProfileStep;
  required: boolean;
  message: string;
}

/** Completitud calculada por reglas (origin RULES), §5. */
export interface Completion {
  origin: 'RULES';
  engine_version: string;
  percent: number;
  status: 'draft' | 'complete';
  can_generate_cv: boolean;
  steps: CompletionStep[];
  missing: MissingField[];
}

/** Secciones editables del perfil (cuerpo de POST/PATCH /profiles/me). */
export interface ProfileSections {
  personal?: Personal;
  headline?: string;
  summary?: string;
  academic_status?: AcademicStatus;
  target?: Target;
  work_conditions?: WorkConditions;
  skills?: SkillItem[];
  experience?: ExperienceItem[];
  education?: EducationItem[];
  languages?: LanguageItem[];
  certifications?: CertificationItem[];
  projects?: Array<Record<string, unknown>>;
  links?: LinkItem[];
  volunteering?: Array<Record<string, unknown>>;
  references_available?: boolean;
  visibility?: ProfileVisibility;
  job_search_status?: JobSearchStatus;
  consents?: Consents;
}

/** Respuesta de GET/POST/PATCH /profiles/me, §4. */
export interface ProfileView extends ProfileSections {
  id: string;
  user_id: string;
  version: number;
  status: 'draft' | 'complete';
  created_at: string;
  updated_at: string;
  personal: Personal;
  cv_files?: Array<{
    stored_filename: string;
    original_filename?: string;
    mime_type: string;
    size_bytes?: number;
    uploaded_at: string;
  }>;
  has_cv_suggestions?: boolean;
  completion: Completion;
}

export interface ApiErrorBody {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

/** Resultado de la extracción del CV (contenido de IA), §6.3. */
export interface CvResult {
  origin: 'AI';
  model?: string;
  prompt_version?: string;
  generated_at?: string;
  verified?: boolean;
  disclaimer: string;
  file?: { filename: string; format: string; size_bytes: number };
  profile_draft: Record<string, unknown>;
  review_fields: string[];
  received_at?: string;
}

/** Trabajo de extracción del CV, §6.2. */
export interface CvJob {
  job_id: string;
  status: 'processing' | 'completed' | 'failed';
  stage?: string;
  step_index?: number;
  progress_percent?: number;
  elapsed_seconds?: number;
  profile_id?: string;
  filename?: string;
  result: CvResult | null;
  error: ApiErrorBody | null;
}
