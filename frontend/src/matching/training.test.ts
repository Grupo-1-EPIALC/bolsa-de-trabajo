import { describe, expect, it } from 'vitest';
import {
  TRAINING_TYPES,
  describeGap,
  jobSteps,
  sortTraining,
  trainingAction,
  trainingType,
} from './training';
import { labelOf } from '../profile/labels';
import type { SkillGap, TrainingItem } from '../types/matching';

const item = (over: Partial<TrainingItem>): TrainingItem => ({
  type: 'course',
  skill: 'React',
  text: 'Curso ficticio',
  priority: 'media',
  ...over,
});

const gap = (over: Partial<SkillGap>): SkillGap => ({
  skill: 'Docker',
  status: 'missing',
  jobs_count: 3,
  share: 0.6,
  required_in: 2,
  current_level: 0,
  required_level: 3,
  priority: 'alta',
  ...over,
});

describe('[UT-FE-03] Matching, Scoring y Recomendaciones de Formación', () => {
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
    expect(labelOf(TRAINING_TYPES, 'skill')).toBe('Competencia para sumar o mejorar');
    expect(trainingAction('processing', false)).toBe('Generando sugerencias…');
    expect(trainingAction('ready', true)).toBe('Volver a pedir sugerencias');
    expect(trainingAction('not_requested', false)).toBe('Pedir sugerencias con IA');
  });
});

describe('[UT-FE-TRN-02] Formación general, sin proyectos ni portfolios', () => {
  it('los proyectos de recomendaciones viejas se muestran como competencia', () => {
    expect(trainingType('project')).toBe('skill');
    expect(trainingType('course')).toBe('course');
    expect(sortTraining([item({ type: 'project' })])[0].type).toBe('skill');
  });

  it('describe cada brecha sobre las ofertas parecidas', () => {
    expect(describeGap(gap({}), 5)).toBe('Obligatoria en 3 de 5 ofertas parecidas');
    expect(describeGap(gap({ required_in: 0, jobs_count: 1 }), 1)).toBe(
      'Deseable en 1 de 1 oferta parecida',
    );
    expect(describeGap(gap({ status: 'improve', current_level: 1 }), 5)).toBe(
      'Tenés nivel 1 y piden 3 en 3 de 5 ofertas parecidas',
    );
  });

  it('en cada oferta sólo quedan los pasos de postularse o mostrar mejor el perfil', () => {
    const steps = [
      { type: 'apply', text: 'Postulate' },
      { type: 'course', text: 'Hacé un curso' },
      { type: 'project', text: 'Armá un portfolio' },
      { type: 'profile_tip', text: 'Cargá Git en tu experiencia' },
    ];
    expect(jobSteps(steps).map((s) => s.type)).toEqual(['apply', 'profile_tip']);
    expect(jobSteps(undefined)).toEqual([]);
  });
});
