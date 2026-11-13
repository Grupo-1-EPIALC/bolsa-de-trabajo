// Tipos de jobs-service según contracts/historico/jobs_frontend.md §9 (sin `any`).
// Los enums comunes con el perfil salen de ./profile (estructura_comun_perfil_oferta_match.md §3).

import type {
  AvailabilityStart,
  ContractDuration,
  Currency,
  EducationLevel,
  EducationStatus,
  EmploymentType,
  LanguageLevel,
  SalaryPeriod,
  SalaryVisibility,
  Seniority,
  Shift,
  SkillCategory,
  WorkModality,
  WorkSchedule,
} from './profile';

export type JobStatus = 'active' | 'closed';
export type JobStatusFilter = JobStatus | 'all';
export type RequirementKind = 'required' | 'desired' | 'excluding';

export interface JobLocation {
  country: string;
  province: string;
  city: string;
  postal_code?: string | null;
  zone?: string | null;
}

export interface VariableCompensation {
  type: 'bonus' | 'commission' | 'profit_sharing';
  description?: string | null;
  max_percent?: number | null;
}

export interface JobSalary {
  min?: number | null;
  max?: number | null;
  currency?: Currency | null;
  period?: SalaryPeriod | null;
  gross?: boolean;
  payment_mode?: 'local' | 'usd' | 'usd_paid_in_local' | null;
  negotiable?: boolean;
  adjustment?: 'none' | 'monthly' | 'quarterly' | 'semiannual' | 'by_agreement' | null;
  variable_compensation?: VariableCompensation[];
  visibility?: SalaryVisibility | null;
  to_agree?: boolean;
  notes?: string | null;
}

export interface JobWorkConditions {
  work_schedule: WorkSchedule[];
  work_modality: WorkModality[];
  hybrid_onsite_days?: number | null;
  employment_type: EmploymentType[];
  contract_duration: ContractDuration[];
  weekly_hours?: { min: number; max: number } | null;
  shifts: Shift[];
  availability_start?: AvailabilityStart | null;
  /** `null` para terceros si la empresa no publica el sueldo (§7). */
  salary?: JobSalary | null;
  relocation_support?: boolean;
  travel_availability?: 'none' | 'occasional' | 'frequent' | null;
  driver_license: string[];
  own_vehicle?: boolean | null;
  own_equipment?: boolean | null;
  invoicing_status?: 'monotributo' | 'responsable_inscripto' | 'none' | 'to_register' | null;
  work_authorization: string[];
  timezone?: string | null;
  timezone_overlap_hours?: number | null;
}

export interface SkillRequirement {
  name: string;
  normalized?: string;
  level: number; // 1–5
  kind: RequirementKind;
  years?: number | null;
  category?: SkillCategory | null;
}

export interface LanguageRequirement {
  name: string;
  normalized?: string;
  level: LanguageLevel;
  kind: RequirementKind;
  certification?: string | null;
}

export interface EducationRequirement {
  institution?: string | null;
  degree?: string | null;
  field?: string | null;
  level: EducationLevel;
  status: EducationStatus;
  progress_percent?: number | null;
  gpa?: number | null;
  kind: RequirementKind;
}

export interface ExperienceRequirement {
  min_years: number;
  area?: string | null;
  kind: RequirementKind;
}

export interface CertificationRequirement {
  name: string;
  kind: RequirementKind;
}

export interface AcademicRequirement {
  min_progress_percent?: number | null;
  careers: string[];
  min_current_year?: number | null;
}

export interface Requirements {
  skills: SkillRequirement[];
  languages: LanguageRequirement[];
  education: EducationRequirement[];
  experience?: ExperienceRequirement | null;
  certifications: CertificationRequirement[];
  academic?: AcademicRequirement | null;
}

export interface CompanySnapshot {
  name: string;
  industry?: string | null;
  size?: '1-10' | '11-50' | '51-200' | '201-1000' | '1000+' | null;
  logo_url?: string | null;
}

export interface JobOpportunity {
  id: string;
  company_id: string;
  company_snapshot: CompanySnapshot;
  status: JobStatus;
  title: string;
  description: string;
  responsibilities: string[];
  area: string;
  seniority: Seniority;
  vacancies: number;
  location: JobLocation;
  work_conditions: JobWorkConditions | null;
  requirements: Requirements;
  benefits: string[];
  created_at: string;
  updated_at: string;
  published_at: string | null;
  expires_at: string | null;
  version: number;
}

export interface JobList {
  items: JobOpportunity[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// Requests: sin company_id, company_snapshot, status, version ni timestamps (§2).

export type SkillRequirementInput = Omit<SkillRequirement, 'normalized'>;
export type LanguageRequirementInput = Omit<LanguageRequirement, 'normalized'>;

export interface RequirementsInput {
  skills: SkillRequirementInput[];
  languages?: LanguageRequirementInput[];
  education?: EducationRequirement[];
  experience?: ExperienceRequirement | null;
  certifications?: CertificationRequirement[];
  academic?: AcademicRequirement | null;
}

export interface JobCreateInput {
  title: string;
  description: string;
  responsibilities?: string[];
  area?: string;
  seniority: Seniority;
  vacancies?: number;
  location: JobLocation;
  work_conditions?: JobWorkConditions | null;
  requirements: RequirementsInput;
  benefits?: string[];
  expires_at?: string | null;
}

export type JobUpdateInput = Partial<JobCreateInput> & { status?: 'active' };

// Postulaciones (contracts/jobs.md, parte A §12).

export interface ApplicantContact {
  name: string;
  email: string;
  phone?: string | null;
}

/** Lo que ve la empresa de quien se postuló: el estudiante lo compartió al postularse. */
export interface Applicant {
  id: string;
  job_id: string;
  /** Mismo id que `candidate.profile_id` del ranking de matching. */
  profile_id: string;
  headline?: string | null;
  contact: ApplicantContact;
  applied_at: string;
  updated_at: string;
}

export interface ApplicantList {
  job_id: string;
  items: Applicant[];
  total: number;
}

export interface MyApplication {
  id: string;
  job_id: string;
  applied_at: string;
  /** `null` si la empresa se dio de baja. */
  job: { title: string; company_id: string; company_name: string; status: JobStatus } | null;
}

export interface MyApplicationList {
  items: MyApplication[];
  total: number;
}
