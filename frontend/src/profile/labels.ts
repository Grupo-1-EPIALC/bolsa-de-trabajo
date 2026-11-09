// Etiquetas es-AR de los enums (contracts/profile.md, parte A §9).

export type Options<T extends string = string> = ReadonlyArray<readonly [T, string]>;

export const WORK_SCHEDULE = [
  ['full_time', 'Full time'],
  ['part_time', 'Part time'],
  ['hourly', 'Por horas'],
  ['flexible', 'Flexible'],
] as const;

export const WORK_MODALITY = [
  ['onsite', 'Presencial'],
  ['remote', 'Remota'],
  ['hybrid', 'Mixta / híbrida'],
] as const;

export const EMPLOYMENT_TYPE = [
  ['employee', 'Relación de dependencia'],
  ['freelance', 'Freelance'],
  ['internship', 'Pasantía'],
  ['trainee', 'Programa trainee'],
] as const;

export const AVAILABILITY_START = [
  ['immediate', 'Inmediata'],
  ['within_15_days', 'En 15 días'],
  ['within_30_days', 'En 30 días'],
  ['to_agree', 'A convenir'],
] as const;

export const SHIFT = [
  ['morning', 'Mañana'],
  ['afternoon', 'Tarde'],
  ['evening', 'Vespertino'],
  ['night', 'Noche'],
  ['weekend', 'Fin de semana'],
  ['rotating', 'Rotativo'],
] as const;

export const SENIORITY = [
  ['no_experience', 'Sin experiencia'],
  ['trainee', 'Trainee'],
  ['junior', 'Junior'],
  ['semi_senior', 'Semi senior'],
  ['senior', 'Senior'],
] as const;

export const SKILL_LEVEL = [
  ['1', 'Inicial'],
  ['2', 'Básico'],
  ['3', 'Intermedio'],
  ['4', 'Avanzado'],
  ['5', 'Experto'],
] as const;

export const SKILL_CATEGORY = [
  ['hard', 'Técnica'],
  ['tool', 'Herramienta'],
  ['methodology', 'Metodología'],
  ['soft', 'Interpersonal'],
] as const;

export const LANGUAGE_LEVEL = [
  ['A1', 'A1'],
  ['A2', 'A2'],
  ['B1', 'B1'],
  ['B2', 'B2'],
  ['C1', 'C1'],
  ['C2', 'C2'],
  ['native', 'Nativo'],
] as const;

export const EDUCATION_LEVEL = [
  ['secondary', 'Secundario'],
  ['tertiary', 'Terciario'],
  ['university', 'Universitario'],
  ['postgraduate', 'Posgrado'],
  ['course', 'Curso'],
] as const;

export const EDUCATION_STATUS = [
  ['in_progress', 'En curso'],
  ['completed', 'Completo'],
  ['incomplete', 'Incompleto'],
] as const;

export const CURRENCY = [
  ['ARS', 'ARS'],
  ['USD', 'USD'],
] as const;

export const SALARY_PERIOD = [
  ['hour', 'por hora'],
  ['day', 'por día'],
  ['month', 'por mes'],
  ['year', 'por año'],
  ['project', 'por proyecto'],
] as const;

export const SALARY_VISIBILITY = [
  ['public', 'Visible para empresas'],
  ['on_match', 'Sólo si hay match'],
  ['hidden', 'Oculto (sólo lo usa el motor)'],
] as const;

export const LINK_TYPE = [
  ['linkedin', 'LinkedIn'],
  ['github', 'GitHub'],
  ['portfolio', 'Portfolio'],
  ['other', 'Otro'],
] as const;

export const PROFILE_VISIBILITY = [
  ['public_to_companies', 'Visible para empresas'],
  ['only_applied', 'Sólo donde me postulo'],
  ['hidden', 'Oculto'],
] as const;

export const JOB_SEARCH_STATUS = [
  ['active', 'Buscando'],
  ['open_to_offers', 'Abierto a ofertas'],
  ['not_looking', 'No busco'],
] as const;

export const STEP_LABEL: Record<string, string> = {
  cv: 'Datos del CV',
  preferences: 'Preferencias laborales',
  privacy: 'Privacidad',
  company: 'Datos de la empresa',
  branding: 'Marca empleadora',
};

// ---- Empresa (contracts/profile.md, parte B §9) ----

export const COMPANY_SIZE = [
  ['1-10', '1 a 10 empleados'],
  ['11-50', '11 a 50'],
  ['51-200', '51 a 200'],
  ['201-1000', '201 a 1000'],
  ['1000+', 'Más de 1000'],
] as const;

export const COMPANY_VISIBILITY = [
  ['public', 'Visible para estudiantes'],
  ['hidden', 'Oculto'],
] as const;

export const COMPANY_MODALITY = [
  ['onsite', 'Presencial'],
  ['remote', 'Remota'],
  ['hybrid', 'Híbrida'],
] as const;

export const COMPANY_LINK_TYPE = [
  ['linkedin', 'LinkedIn'],
  ['instagram', 'Instagram'],
  ['x', 'X'],
  ['facebook', 'Facebook'],
  ['youtube', 'YouTube'],
  ['github', 'GitHub'],
  ['other', 'Otro'],
] as const;

// ---- Búsquedas (contracts/jobs.md, parte B §10) ----

export const JOB_STATUS = [
  ['active', 'Activa'],
  ['closed', 'Cerrada'],
] as const;

export const JOB_STATUS_FILTER = [
  ['active', 'Activas'],
  ['closed', 'Cerradas'],
  ['all', 'Todas'],
] as const;

export const REQUIREMENT_KIND = [
  ['required', 'Obligatorio'],
  ['desired', 'Deseable'],
  ['excluding', 'Excluyente'],
] as const;

export const CONTRACT_DURATION = [
  ['permanent', 'Indefinido'],
  ['fixed_term', 'Plazo fijo'],
  ['project', 'Por proyecto'],
  ['seasonal', 'Temporada'],
] as const;

/** Visibilidad del sueldo de una búsqueda (la ve la empresa al publicar). */
export const JOB_SALARY_VISIBILITY = [
  ['public', 'Público'],
  ['on_match', 'Sólo para los que hacen match'],
  ['hidden', 'Oculto (sólo lo usa el motor)'],
] as const;

/** Etiqueta de un valor dentro de una lista de opciones (o el valor si no está). */
export function labelOf(options: Options, value: unknown): string {
  return options.find(([v]) => v === value)?.[1] ?? String(value ?? '');
}
