// Perfil de empresa según contracts/company_profile_frontend.md (profile-service v0.2.0).
import type { Completion, Location, WorkModality } from './profile';

export type CompanySize = '1-10' | '11-50' | '51-200' | '201-1000' | '1000+';
export type CompanyLinkType =
  'linkedin' | 'instagram' | 'x' | 'facebook' | 'youtube' | 'github' | 'other';
export type CompanyStep = 'company' | 'branding';

export interface CompanyContact {
  email?: string;
  phone?: string;
  name?: string;
  public: boolean;
}

export interface CompanyHiring {
  areas?: string[];
  hires_students?: boolean;
  internship_program?: boolean;
  internship_agreements?: string[];
}

export interface InclusiveHiring {
  accepts_disability_certificate?: boolean;
  accessible_workplace?: boolean;
}

/** Secciones editables (cuerpo de POST/PATCH /profiles/companies/me), §6. */
export interface CompanySections {
  display_name?: string;
  tagline?: string;
  description?: string;
  industry?: string;
  size?: CompanySize;
  founded_year?: number;
  location?: Location;
  offices?: Location[];
  website?: string;
  links?: Array<{ type: CompanyLinkType; url: string }>;
  contact?: CompanyContact;
  work_modalities?: WorkModality[];
  benefits?: string[];
  values?: string[];
  hiring?: CompanyHiring;
  inclusive_hiring?: InclusiveHiring;
  visibility?: 'public' | 'hidden';
}

/** Respuesta de /profiles/companies/me (dueña), §4. */
export interface CompanyProfile extends CompanySections {
  id: string;
  company_id: string;
  version: number;
  status: 'draft' | 'complete';
  created_at: string;
  updated_at: string;
  legal: { legal_name: string; cuit: string; activity: string };
  name: string;
  logo?: { mime_type: string; size_bytes: number; uploaded_at: string };
  logo_url?: string;
  completion: Omit<Completion, 'steps'> & {
    steps: Array<{
      step: CompanyStep;
      complete: boolean;
      missing_required: number;
      missing_recommended: number;
    }>;
  };
}
