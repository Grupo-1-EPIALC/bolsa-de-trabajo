import { describe, expect, it } from 'vitest';
import { TRAINING_TYPES, sortTraining, trainingAction } from './training';
import { labelOf } from '../profile/labels';
import type { TrainingItem } from '../types/matching';

const item = (over: Partial<TrainingItem>): TrainingItem => ({
  type: 'course',
  skill: 'React',
  text: 'Curso ficticio',
  priority: 'media',
  ...over,
});

describe('UT-FE-TRAIN-01 formación sugerida por IA', () => {
  it('ordena de prioridad alta a baja, respeta el orden original y corta en 5', () => {
    const items = [
      item({ text: 'b1', priority: 'baja' }),
      item({ text: 'a1', priority: 'alta' }),
      item({ text: 'm1', priority: 'media' }),
      item({ text: 'a2', priority: 'alta' }),
      item({ text: 'm2', priority: 'media' }),
      item({ text: 'b2', priority: 'baja' }),
    ];
    expect(sortTraining(items).map((i) => i.text)).toEqual(['a1', 'a2', 'm1', 'm2', 'b1']);
  });

  it('descarta ítems sin texto y tolera la lista vacía', () => {
    expect(sortTraining([item({ text: '  ' }), item({ text: 'ok' })]).map((i) => i.text)).toEqual([
      'ok',
    ]);
    expect(sortTraining(undefined)).toEqual([]);
  });

  it('etiquetas en español y texto del botón según el estado', () => {
    expect(labelOf(TRAINING_TYPES, 'profile_tip')).toBe('Consejo para tu perfil');
    expect(trainingAction('processing', false)).toBe('Generando sugerencias…');
    expect(trainingAction('ready', true)).toBe('Volver a pedir sugerencias');
    expect(trainingAction('not_requested', false)).toBe('Pedir sugerencias con IA');
  });
});
