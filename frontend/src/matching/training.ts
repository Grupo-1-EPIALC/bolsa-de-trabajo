// Formación sugerida por IA para una oferta (contracts/matching.md, parte B §B.2).
import type { Options } from '../profile/labels';
import type { Priority, TrainingItem } from '../types/matching';

export const TRAINING_TYPES: Options<TrainingItem['type']> = [
  ['course', 'Curso'],
  ['project', 'Proyecto'],
  ['profile_tip', 'Consejo para tu perfil'],
];

export const TRAINING_ICONS: Record<TrainingItem['type'], string> = {
  course: 'bi-mortarboard',
  project: 'bi-tools',
  profile_tip: 'bi-person-check',
};

const PRIORITY_ORDER: Record<Priority, number> = { alta: 0, media: 1, baja: 2 };

/** Ítems listos para mostrar: con texto, de prioridad alta a baja y como mucho 5. */
export function sortTraining(items: readonly TrainingItem[] | undefined): TrainingItem[] {
  return (items ?? [])
    .filter((item) => item.text?.trim())
    .map((item, index) => ({ item, index }))
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
