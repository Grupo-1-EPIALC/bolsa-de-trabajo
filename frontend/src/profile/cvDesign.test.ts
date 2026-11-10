import { describe, expect, it } from 'vitest';
import { aiAction, aiNote, describeOrder, isAiPending, layoutName } from './cvDesign';
import type { CvDesignView } from '../types/profile';

const view = (over: Partial<CvDesignView> = {}): CvDesignView => ({
  profile_id: 'prof-ficticio',
  effective: {
    id: 'cronologico',
    name: 'Cronológico',
    description: '',
    best_for: '',
    section_order: ['summary', 'experience', 'projects', 'education'],
    source: 'rules',
  },
  rule_based: {
    origin: 'RULES',
    engine_version: 'cv-layout-1.0.0',
    layout: 'cronologico',
    section_order: ['summary', 'experience'],
    reasons: ['Motivo ficticio'],
  },
  ai_recommendation: null,
  user_choice: null,
  catalog: [
    { id: 'cronologico', name: 'Cronológico', description: '', best_for: '', section_order: [] },
    {
      id: 'primer_empleo',
      name: 'Primer empleo',
      description: '',
      best_for: '',
      section_order: [],
    },
  ],
  ...over,
});

const ai = (over: Partial<NonNullable<CvDesignView['ai_recommendation']>> = {}) => ({
  origin: 'AI' as const,
  status: 'completed' as const,
  request_id: 'cvd-ficticio',
  requested_at: '2026-11-10T00:00:00Z',
  layout: 'primer_empleo' as const,
  section_order: [],
  rationale: 'Motivo ficticio',
  model: 'modelo-ficticio',
  prompt_version: '1.0.0',
  generated_at: '2026-11-10T00:00:05Z',
  disclaimer: 'Aviso ficticio',
  stale: false,
  error: null,
  ...over,
});

describe('[UT-FE-CVD-01] Diseño del CV', () => {
  it('muestra las primeras secciones del diseño con sus títulos estándar', () => {
    expect(describeOrder(['summary', 'education', 'projects', 'skills', 'experience'])).toBe(
      'Perfil profesional → Educación → Proyectos → Competencias',
    );
    expect(describeOrder(['summary', 'skills'], 1)).toBe('Perfil profesional');
  });

  it('nombra el diseño según el catálogo', () => {
    expect(layoutName(view(), 'primer_empleo')).toBe('Primer empleo');
    expect(layoutName(view(), null)).toBe('');
  });

  it('sigue consultando mientras la IA está eligiendo', () => {
    expect(isAiPending(view({ ai_recommendation: ai({ status: 'processing' }) }))).toBe(true);
    expect(isAiPending(view({ ai_recommendation: ai() }))).toBe(false);
    expect(isAiPending(null)).toBe(false);
  });

  it('cambia el texto del botón según el estado de la sugerencia', () => {
    expect(aiAction(view(), false)).toBe('Pedir sugerencia a la IA');
    expect(aiAction(view(), true)).toBe('Eligiendo el diseño…');
    expect(aiAction(view({ ai_recommendation: ai() }), false)).toBe('Volver a pedir sugerencia');
    expect(aiAction(view({ ai_recommendation: ai({ stale: true }) }), false)).toBe(
      'Pedir sugerencia a la IA',
    );
  });

  it('explica cuándo la sugerencia de la IA no se aplica', () => {
    expect(aiNote(view())).toBeNull();
    expect(aiNote(view({ ai_recommendation: ai() }))).toBeNull();
    expect(aiNote(view({ ai_recommendation: ai({ stale: true }) }))).toMatch(/Cambiaste tu perfil/);
    expect(aiNote(view({ ai_recommendation: ai({ status: 'failed', error: 'sin cupo' }) }))).toBe(
      'No se pudo obtener la sugerencia: sin cupo',
    );
    expect(
      aiNote(
        view({
          ai_recommendation: ai(),
          user_choice: { layout: 'cronologico', chosen_at: '2026-11-10T00:00:00Z' },
        }),
      ),
    ).toMatch(/a mano/);
  });
});
