// Formulario de búsqueda ↔ JobCreateInput (contracts/jobs_frontend.md §3 y §4).
// PATCH reemplaza bloques enteros: al editar se conservan los campos que el formulario no muestra.
import { ApiError } from '../services/api';
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
  WorkModality,
  WorkSchedule,
} from '../types/profile';
import type {
  JobCreateInput,
  JobOpportunity,
  JobSalary,
  JobWorkConditions,
  RequirementKind,
} from '../types/jobs';

export interface SkillRow {
  name: string;
  level: number;
  kind: RequirementKind;
}

export interface LanguageRow {
  name: string;
  level: LanguageLevel | '';
  kind: RequirementKind;
}

export interface EducationRow {
  level: EducationLevel | '';
  status: EducationStatus | '';
  field: string;
  kind: RequirementKind;
}

export type SalaryMode = 'none' | 'range' | 'to_agree';

export interface JobForm {
  title: string;
  description: string;
  area: string;
  seniority: Seniority | '';
  vacancies: string;
  country: string;
  province: string;
  city: string;
  responsibilities: string; // una por línea
  benefits: string; // uno por línea
  expiresAt: string; // YYYY-MM-DD o ''
  workSchedule: WorkSchedule[];
  workModality: WorkModality[];
  hybridDays: string;
  employmentType: EmploymentType[];
  contractDuration: ContractDuration[];
  shifts: Shift[];
  availabilityStart: AvailabilityStart | '';
  hoursMin: string;
  hoursMax: string;
  salaryMode: SalaryMode;
  salaryMin: string;
  salaryMax: string;
  currency: Currency;
  period: SalaryPeriod;
  salaryVisibility: SalaryVisibility;
  gross: boolean;
  skills: SkillRow[];
  languages: LanguageRow[];
  education: EducationRow[];
  experienceYears: string;
  experienceArea: string;
  experienceKind: RequirementKind;
}

/** Campos del formulario que pueden tener un error para mostrar. */
export type JobFormField =
  | 'title'
  | 'description'
  | 'area'
  | 'seniority'
  | 'vacancies'
  | 'country'
  | 'province'
  | 'city'
  | 'expiresAt'
  | 'hybridDays'
  | 'hours'
  | 'salary'
  | 'skills'
  | 'languages'
  | 'education'
  | 'experience'
  | 'workConditions'
  | 'form';

export type JobFormErrors = Partial<Record<JobFormField, string>>;

export const newSkill = (): SkillRow => ({ name: '', level: 3, kind: 'required' });
export const newLanguage = (): LanguageRow => ({ name: '', level: '', kind: 'desired' });
export const newEducation = (): EducationRow => ({
  level: '',
  status: '',
  field: '',
  kind: 'desired',
});

export function emptyJobForm(): JobForm {
  return {
    title: '',
    description: '',
    area: '',
    seniority: '',
    vacancies: '1',
    country: 'AR',
    province: '',
    city: '',
    responsibilities: '',
    benefits: '',
    expiresAt: '',
    workSchedule: [],
    workModality: [],
    hybridDays: '',
    employmentType: [],
    contractDuration: [],
    shifts: [],
    availabilityStart: '',
    hoursMin: '',
    hoursMax: '',
    salaryMode: 'none',
    salaryMin: '',
    salaryMax: '',
    currency: 'ARS',
    period: 'month',
    salaryVisibility: 'public',
    gross: true,
    skills: [newSkill()],
    languages: [],
    education: [],
    experienceYears: '',
    experienceArea: '',
    experienceKind: 'required',
  };
}

const str = (value: number | null | undefined) => (typeof value === 'number' ? String(value) : '');
const lines = (items: string[]) => items.join('\n');

/** Precarga el formulario con una búsqueda existente (la empresa dueña la ve completa). */
export function jobToForm(job: JobOpportunity): JobForm {
  const wc = job.work_conditions;
  const salary = wc?.salary ?? null;
  const hasAmount = typeof salary?.min === 'number' || typeof salary?.max === 'number';
  const experience = job.requirements.experience;
  return {
    ...emptyJobForm(),
    title: job.title,
    description: job.description,
    area: job.area ?? '',
    seniority: job.seniority,
    vacancies: String(job.vacancies),
    country: job.location.country,
    province: job.location.province,
    city: job.location.city,
    responsibilities: lines(job.responsibilities),
    benefits: lines(job.benefits),
    expiresAt: job.expires_at ? job.expires_at.slice(0, 10) : '',
    workSchedule: wc?.work_schedule ?? [],
    workModality: wc?.work_modality ?? [],
    hybridDays: str(wc?.hybrid_onsite_days),
    employmentType: wc?.employment_type ?? [],
    contractDuration: wc?.contract_duration ?? [],
    shifts: wc?.shifts ?? [],
    availabilityStart: wc?.availability_start ?? '',
    hoursMin: str(wc?.weekly_hours?.min),
    hoursMax: str(wc?.weekly_hours?.max),
    salaryMode: !salary ? 'none' : salary.to_agree || !hasAmount ? 'to_agree' : 'range',
    salaryMin: str(salary?.min),
    salaryMax: str(salary?.max),
    currency: salary?.currency ?? 'ARS',
    period: salary?.period ?? 'month',
    salaryVisibility: salary?.visibility ?? 'public',
    gross: salary?.gross ?? true,
    skills: job.requirements.skills.map(({ name, level, kind }) => ({ name, level, kind })),
    languages: job.requirements.languages.map(({ name, level, kind }) => ({ name, level, kind })),
    education: job.requirements.education.map(({ level, status, field, kind }) => ({
      level,
      status,
      field: field ?? '',
      kind,
    })),
    experienceYears: str(experience?.min_years),
    experienceArea: experience?.area ?? '',
    experienceKind: experience?.kind ?? 'required',
  };
}

const toNumber = (value: string): number | null => {
  const trimmed = value.trim();
  if (trimmed === '') return null;
  const n = Number(trimmed.replace(',', '.'));
  return Number.isFinite(n) ? n : NaN;
};

const splitLines = (value: string) =>
  value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);

/** Fin del día elegido, en hora local, como ISO-8601. */
export function endOfDayIso(day: string): string {
  return new Date(`${day}T23:59:59`).toISOString();
}

/** Mismas reglas que jobs-service (§3) para avisar antes de enviar. */
export function validateJobForm(form: JobForm, now: Date = new Date()): JobFormErrors {
  const errors: JobFormErrors = {};
  if (!form.title.trim()) errors.title = 'Poné un título.';
  else if (form.title.trim().length > 200) errors.title = 'Máximo 200 caracteres.';
  if (!form.description.trim()) errors.description = 'Describí la búsqueda.';
  if (!form.seniority) errors.seniority = 'Elegí el seniority.';
  const vacancies = toNumber(form.vacancies);
  if (vacancies === null || !Number.isInteger(vacancies) || vacancies < 1 || vacancies > 1000) {
    errors.vacancies = 'Entre 1 y 1000.';
  }
  if (!/^[A-Za-z]{2}$/.test(form.country.trim())) errors.country = 'Código de 2 letras (ej. AR).';
  if (!form.province.trim()) errors.province = 'Completá la provincia.';
  if (!form.city.trim()) errors.city = 'Completá la ciudad.';

  const skills = form.skills.filter((s) => s.name.trim());
  if (skills.length === 0) errors.skills = 'Agregá al menos una competencia.';
  else if (!skills.some((s) => s.kind === 'required')) {
    errors.skills = 'Al menos una competencia tiene que ser obligatoria.';
  } else if (skills.some((s) => s.level < 1 || s.level > 5)) {
    errors.skills = 'El nivel va de 1 a 5.';
  }
  if (form.languages.some((l) => !l.name.trim() || !l.level)) {
    errors.languages = 'Completá el idioma y el nivel, o quitá la fila.';
  }
  if (form.education.some((e) => !e.level || !e.status)) {
    errors.education = 'Completá el nivel y el estado, o quitá la fila.';
  }
  const years = toNumber(form.experienceYears);
  if (years !== null && (Number.isNaN(years) || years < 0 || years > 60)) {
    errors.experience = 'Los años de experiencia van de 0 a 60.';
  }

  const hoursMin = toNumber(form.hoursMin);
  const hoursMax = toNumber(form.hoursMax);
  if ((hoursMin === null) !== (hoursMax === null)) {
    errors.hours = 'Completá el mínimo y el máximo de horas.';
  } else if (hoursMin !== null && hoursMax !== null) {
    const valid = (n: number) => Number.isInteger(n) && n >= 0 && n <= 168;
    if (!valid(hoursMin) || !valid(hoursMax)) errors.hours = 'Las horas van de 0 a 168.';
    else if (hoursMin > hoursMax) errors.hours = 'El mínimo no puede superar al máximo.';
  }
  const hybridDays = toNumber(form.hybridDays);
  if (hybridDays !== null && (!Number.isInteger(hybridDays) || hybridDays < 0 || hybridDays > 5)) {
    errors.hybridDays = 'Entre 0 y 5 días.';
  }

  if (form.salaryMode === 'range') {
    const min = toNumber(form.salaryMin);
    const max = toNumber(form.salaryMax);
    if (min === null && max === null)
      errors.salary = 'Poné al menos un monto o elegí "A convenir".';
    else if ([min, max].some((n) => n !== null && (Number.isNaN(n) || n < 0))) {
      errors.salary = 'Los montos tienen que ser positivos.';
    } else if (min !== null && max !== null && min > max) {
      errors.salary = 'El mínimo no puede superar al máximo.';
    }
  }
  if (form.expiresAt && new Date(endOfDayIso(form.expiresAt)) <= now) {
    errors.expiresAt = 'La fecha de cierre tiene que ser futura.';
  }
  return errors;
}

/**
 * Errores que siguen vigentes después de editar: sólo los campos que ya tenían error y todavía
 * no cumplen las reglas. Los errores del servidor (`form`) se descartan al editar.
 */
export function pendingErrors(previous: JobFormErrors, form: JobForm, now: Date = new Date()) {
  const current = validateJobForm(form, now);
  const kept: JobFormErrors = {};
  for (const field of Object.keys(previous) as JobFormField[]) {
    if (field !== 'form' && current[field]) kept[field] = current[field];
  }
  return kept;
}

function buildSalary(form: JobForm, base: JobSalary | null | undefined): JobSalary | null {
  if (form.salaryMode === 'none') return null;
  const common = {
    ...(base ?? {}),
    currency: form.currency,
    period: form.period,
    visibility: form.salaryVisibility,
    gross: form.gross,
  };
  if (form.salaryMode === 'to_agree') return { ...common, min: null, max: null, to_agree: true };
  return {
    ...common,
    min: toNumber(form.salaryMin),
    max: toNumber(form.salaryMax),
    to_agree: false,
  };
}

function buildWorkConditions(
  form: JobForm,
  base: JobWorkConditions | null | undefined,
): JobWorkConditions {
  const hoursMin = toNumber(form.hoursMin);
  const hoursMax = toNumber(form.hoursMax);
  return {
    // Lo que el formulario no edita (licencias, zona horaria, etc.) se conserva.
    driver_license: [],
    work_authorization: [],
    ...(base ?? {}),
    work_schedule: form.workSchedule,
    work_modality: form.workModality,
    hybrid_onsite_days: form.workModality.includes('hybrid') ? toNumber(form.hybridDays) : null,
    employment_type: form.employmentType,
    contract_duration: form.contractDuration,
    shifts: form.shifts,
    availability_start: form.availabilityStart || null,
    weekly_hours: hoursMin !== null && hoursMax !== null ? { min: hoursMin, max: hoursMax } : null,
    salary: buildSalary(form, base?.salary),
  };
}

/** Cuerpo para POST (o PATCH completo) a partir del formulario. `base` = la búsqueda editada. */
export function formToInput(form: JobForm, base?: JobOpportunity): JobCreateInput {
  const years = toNumber(form.experienceYears);
  return {
    title: form.title.trim(),
    description: form.description.trim(),
    responsibilities: splitLines(form.responsibilities),
    area: form.area.trim(),
    seniority: form.seniority as Seniority,
    vacancies: toNumber(form.vacancies) ?? 1,
    location: {
      ...(base?.location ?? {}),
      country: form.country.trim().toUpperCase(),
      province: form.province.trim(),
      city: form.city.trim(),
    },
    work_conditions: buildWorkConditions(form, base?.work_conditions),
    requirements: {
      skills: form.skills
        .filter((s) => s.name.trim())
        .map((s) => ({ name: s.name.trim(), level: s.level, kind: s.kind })),
      languages: form.languages.map((l) => ({
        name: l.name.trim(),
        level: l.level as LanguageLevel,
        kind: l.kind,
      })),
      education: form.education.map((e) => ({
        level: e.level as EducationLevel,
        status: e.status as EducationStatus,
        field: e.field.trim() || null,
        kind: e.kind,
      })),
      experience:
        years === null
          ? null
          : {
              min_years: years,
              area: form.experienceArea.trim() || null,
              kind: form.experienceKind,
            },
      certifications: (base?.requirements.certifications ?? []).map(({ name, kind }) => ({
        name,
        kind,
      })),
      academic: base?.requirements.academic ?? null,
    },
    benefits: splitLines(form.benefits),
    expires_at: form.expiresAt ? endOfDayIso(form.expiresAt) : null,
  };
}

const FIELD_BY_PATH: Array<[RegExp, JobFormField]> = [
  [/^title/, 'title'],
  [/^description/, 'description'],
  [/^area/, 'area'],
  [/^seniority/, 'seniority'],
  [/^vacancies/, 'vacancies'],
  [/^location\.country/, 'country'],
  [/^location\.province/, 'province'],
  [/^location\.city/, 'city'],
  [/^expires_at/, 'expiresAt'],
  [/^work_conditions\.hybrid_onsite_days/, 'hybridDays'],
  [/^work_conditions\.weekly_hours/, 'hours'],
  [/^work_conditions\.salary/, 'salary'],
  [/^work_conditions/, 'workConditions'],
  [/^requirements\.skills/, 'skills'],
  [/^requirements\.languages/, 'languages'],
  [/^requirements\.education/, 'education'],
  [/^requirements\.experience/, 'experience'],
  [/^requirements/, 'skills'],
];

function fieldOf(path: string): JobFormField {
  return FIELD_BY_PATH.find(([re]) => re.test(path))?.[1] ?? 'form';
}

/**
 * Errores por campo a partir de un 422 de jobs-service: `details.errors[].loc` (Pydantic) o
 * `details.field` (reglas de negocio, p. ej. UT-JOBS-01).
 */
export function fieldErrorsFromApi(err: unknown): JobFormErrors {
  if (!(err instanceof ApiError) || err.status !== 422) return {};
  const errors: JobFormErrors = {};
  const list = err.details.errors;
  if (Array.isArray(list)) {
    for (const item of list as Array<{ loc?: unknown[]; msg?: string }>) {
      const path = (item.loc ?? [])
        .filter((part) => part !== 'body' && typeof part !== 'number')
        .join('.');
      const field = fieldOf(path);
      errors[field] ??= item.msg ?? 'Revisá este dato.';
    }
  }
  const field = err.details.field;
  if (typeof field === 'string') errors[fieldOf(field)] ??= err.message;
  if (Object.keys(errors).length === 0) errors.form = err.message;
  return errors;
}
