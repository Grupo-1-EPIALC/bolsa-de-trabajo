// Qué competencias sumar o mejorar, en general (contracts/matching.md, parte B §B.2).
import type { Options } from '../profile/labels';
import type {
  NextStep,
  Priority,
  SkillGap,
  TrainingItem,
  TrainingItemType,
} from '../types/matching';

export const TRAINING_TYPES: Options<TrainingItemType> = [
  ['course', 'Curso'],
  ['skill', 'Competencia para sumar o mejorar'],
  ['profile_tip', 'Consejo para tu perfil'],
];

export const TRAINING_ICONS: Record<TrainingItemType, string> = {
  course: 'bi-mortarboard',
  skill: 'bi-graph-up-arrow',
  profile_tip: 'bi-person-check',
};

const PRIORITY_ORDER: Record<Priority, number> = { alta: 0, media: 1, baja: 2 };

/** Las recomendaciones viejas podían traer `project`: se muestran como competencia. */
export function trainingType(type: string): TrainingItemType {
  return type === 'course' || type === 'profile_tip' ? type : 'skill';
}

/** Ítems listos para mostrar: con texto, de prioridad alta a baja y como mucho 5. */
export function sortTraining(items: readonly TrainingItem[] | undefined): TrainingItem[] {
  return (items ?? [])
    .filter((item) => item.text?.trim())
    .map((item, index) => ({ item: { ...item, type: trainingType(item.type) }, index }))
    .sort(
      (a, b) =>
        (PRIORITY_ORDER[a.item.priority] ?? 3) - (PRIORITY_ORDER[b.item.priority] ?? 3) ||
        a.index - b.index,
    )
    .map(({ item }) => item)
    .slice(0, 5);
}

/** Texto del botón según el estado del bloque de IA. */
export function trainingAction(status: string | undefined, hasItems: boolean): string {
  if (status === 'pending' || status === 'processing') return 'Generando sugerencias…';
  if (hasItems) return 'Volver a pedir sugerencias';
  return 'Pedir sugerencias con IA';
}

/** "Obligatoria en 3 de 5 ofertas parecidas" / "Tenés nivel 1 y piden 3 en …". */
export function describeGap(gap: SkillGap, similarJobs: number): string {
  const offers = similarJobs === 1 ? 'oferta parecida' : 'ofertas parecidas';
  const where = `en ${gap.jobs_count} de ${similarJobs} ${offers}`;
  const kind =
    gap.required_in === 0
      ? ' (deseable)'
      : gap.required_in < gap.jobs_count
        ? ` (obligatoria en ${gap.required_in})`
        : '';
  if (gap.status === 'improve') {
    return `Tenés nivel ${gap.current_level} y piden ${gap.required_level} ${where}${kind}`;
  }
  if (gap.required_in === gap.jobs_count) return `Obligatoria ${where}`;
  return `Falta ${where}${kind}`;
}

/** Pasos de una oferta: sólo postularse o mostrar mejor algo que ya tiene. Los cursos y lo que
 * conviene aprender van en "Qué sumar o mejorar" (general); se filtran de recomendaciones viejas. */
export function jobSteps(steps: readonly NextStep[] | undefined): NextStep[] {
  return (steps ?? []).filter((s) => s.type === 'apply' || s.type === 'profile_tip');
}
