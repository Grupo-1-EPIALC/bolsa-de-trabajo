// Diseño del CV: textos y decisiones de pantalla (contracts/profile.md, parte A §8.1).
import type { CvDesignView, CvLayoutId, CvSectionKey } from '../types/profile';

export const SECTION_LABELS: Record<CvSectionKey, string> = {
  summary: 'Perfil profesional',
  skills: 'Competencias',
  experience: 'Experiencia',
  projects: 'Proyectos',
  education: 'Educación',
  languages: 'Idiomas',
  certifications: 'Certificaciones',
  volunteering: 'Voluntariado',
};

export const SOURCE_LABELS: Record<CvDesignView['effective']['source'], string> = {
  user: 'Elegido por vos',
  ai: 'Sugerido por IA',
  rules: 'Calculado por reglas',
};

/** Las primeras secciones del diseño, para mostrar qué queda arriba. */
export function describeOrder(order: readonly CvSectionKey[], max = 4): string {
  return order
    .slice(0, max)
    .map((key) => SECTION_LABELS[key] ?? key)
    .join(' → ');
}

/** Nombre del diseño según el catálogo (o el id si no está). */
export function layoutName(view: CvDesignView, id: CvLayoutId | null | undefined): string {
  if (!id) return '';
  return view.catalog.find((layout) => layout.id === id)?.name ?? id;
}

/** La sugerencia de la IA está en curso: hay que seguir consultando. */
export function isAiPending(view: CvDesignView | null): boolean {
  return view?.ai_recommendation?.status === 'processing';
}

/** Texto del botón de la IA según el estado de la sugerencia. */
export function aiAction(view: CvDesignView | null, busy: boolean): string {
  if (busy || isAiPending(view)) return 'Eligiendo el diseño…';
  const ai = view?.ai_recommendation;
  if (ai?.status === 'completed' && !ai.stale) return 'Volver a pedir sugerencia';
  return 'Pedir sugerencia a la IA';
}

/**
 * Qué decir de la sugerencia de la IA. Nunca se muestra un puntaje: la IA sólo elige
 * el orden de las secciones.
 */
export function aiNote(view: CvDesignView): string | null {
  const ai = view.ai_recommendation;
  if (!ai) return null;
  if (ai.status === 'failed') {
    return ai.error
      ? `No se pudo obtener la sugerencia: ${ai.error}`
      : 'No se pudo obtener la sugerencia.';
  }
  if (ai.status === 'completed' && ai.stale) {
    return 'Cambiaste tu perfil desde la última sugerencia: pedila de nuevo para que la IA lo tenga en cuenta.';
  }
  if (ai.status === 'completed' && view.user_choice) {
    return 'Elegiste un diseño a mano: la sugerencia de la IA no se aplica.';
  }
  return null;
}
