// Reglas puras del formulario de perfil (sin React): placeholders de la IA, limpieza del
// payload antes del PATCH y paso pendiente según la completitud calculada por reglas.
import type { Completion, ProfileSections, ProfileStep, ProfileView } from '../types/profile';

/** Marca que deja la IA en los escalares que no encontró en el CV (contrato §6.3). */
export const PLACEHOLDER = 'COMPLETAR_MANUALMENTE';

export const STEP_ORDER: ProfileStep[] = ['cv', 'preferences', 'privacy'];

/** Secciones que se editan en el paso 1 ("Datos del CV"). */
export const CV_STEP_SECTIONS = [
  'personal',
  'headline',
  'summary',
  'academic_status',
  'skills',
  'experience',
  'education',
  'languages',
  'certifications',
  'links',
] as const;

type Json = unknown;

/** Copia profunda reemplazando cada PLACEHOLDER por '' (campo vacío a completar). */
export function stripPlaceholders<T extends Json>(value: T): T {
  if (value === PLACEHOLDER) return '' as T;
  if (Array.isArray(value)) return value.map((v) => stripPlaceholders(v)) as T;
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, Json>).map(([k, v]) => [k, stripPlaceholders(v)]),
    ) as T;
  }
  return value;
}

/** Rutas (estilo `skills[1].level`) donde todavía queda un PLACEHOLDER. */
export function findPlaceholders(value: Json, path = ''): string[] {
  if (value === PLACEHOLDER) return [path];
  if (Array.isArray(value)) {
    return value.flatMap((v, i) => findPlaceholders(v, `${path}[${i}]`));
  }
  if (value && typeof value === 'object') {
    return Object.entries(value as Record<string, Json>).flatMap(([k, v]) =>
      findPlaceholders(v, path ? `${path}.${k}` : k),
    );
  }
  return [];
}

/**
 * Quita de los objetos las claves vacías ('' / undefined / null) para no mandar
 * opcionales inválidos (p. ej. teléfono vacío). Las listas se conservan aunque estén vacías.
 */
export function compact<T extends Json>(value: T): T {
  if (Array.isArray(value)) return value.map((v) => compact(v)) as T;
  if (value && typeof value === 'object') {
    const entries = Object.entries(value as Record<string, Json>)
      .filter(([, v]) => v !== '' && v !== undefined && v !== null)
      .map(([k, v]) => [k, compact(v)] as const);
    return Object.fromEntries(entries) as T;
  }
  return value;
}

/** Primer paso con `complete = false`, o null si el perfil está completo. */
export function firstIncompleteStep(completion: Completion | undefined): ProfileStep | null {
  if (!completion) return 'cv';
  const pending = STEP_ORDER.find((step) => {
    const info = completion.steps.find((s) => s.step === step);
    return !info || !info.complete;
  });
  return pending ?? null;
}

/**
 * Datos iniciales del paso 1: lo que sugirió la IA (sin placeholders) pisa a lo guardado
 * sólo en las secciones que trae el borrador. El perfil guardado nunca se modifica acá.
 */
export function mergeDraft(
  profile: ProfileView | null,
  draft: Record<string, unknown> | null,
): ProfileSections {
  const base: Record<string, unknown> = {};

  for (const key of CV_STEP_SECTIONS) {
    const fromProfile = profile?.[key as keyof ProfileView];
    const fromDraft = draft?.[key];

    // 💡 LÓGICA DE COMPARATIVA:
    // Si el usuario YA TIENE un dato persistido/confirmado en el perfil real,
    // se respeta su dato. Si el campo en el perfil está vacío, se muestra la sugerencia de la IA.
    if (fromProfile !== undefined && fromProfile !== null && fromProfile !== '') {
      base[key] = fromProfile;
    } else if (fromDraft !== undefined) {
      base[key] = stripPlaceholders(fromDraft);
    }
  }

  return base as ProfileSections;
}

/** Normaliza una ruta de review_fields para compararla con la de un input. */
export function reviewKey(path: string): string {
  return path.replace(/\[(\d+)\]/g, '.$1');
}
