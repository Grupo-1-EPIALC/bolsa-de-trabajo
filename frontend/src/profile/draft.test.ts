import { describe, expect, it } from 'vitest';
import {
  PLACEHOLDER,
  compact,
  fieldKeys,
  findPlaceholders,
  firstIncompleteStep,
  mergeDraft,
  reviewKey,
  stripPlaceholders,
} from './draft';
import type { Completion, ProfileView } from '../types/profile';

const completion = (cv: boolean, preferences: boolean, privacy: boolean): Completion => ({
  origin: 'RULES',
  engine_version: '1.0.0',
  percent: 50,
  status: cv && preferences && privacy ? 'complete' : 'draft',
  can_generate_cv: cv,
  steps: [
    { step: 'cv', complete: cv, missing_required: 0, missing_recommended: 0 },
    { step: 'preferences', complete: preferences, missing_required: 0, missing_recommended: 0 },
    { step: 'privacy', complete: privacy, missing_required: 0, missing_recommended: 0 },
  ],
  missing: [],
});

describe('[UT-FE-02] Perfil de Estudiante y Sanitización de CV', () => {
  describe('placeholders de la IA', () => {
    const draft = {
      headline: PLACEHOLDER,
      personal: { name: 'Ana Ficticia', phone: PLACEHOLDER },
      skills: [
        { name: 'Python', level: 4 },
        { name: 'Docker', level: PLACEHOLDER },
      ],
    };

    it('encuentra las rutas con COMPLETAR_MANUALMENTE', () => {
      expect(findPlaceholders(draft)).toEqual(['headline', 'personal.phone', 'skills[1].level']);
    });

    it('los reemplaza por campos vacíos sin tocar el resto', () => {
      const clean = stripPlaceholders(draft);
      expect(clean.headline).toBe('');
      expect(clean.personal).toEqual({ name: 'Ana Ficticia', phone: '' });
      expect(clean.skills[0]).toEqual({ name: 'Python', level: 4 });
      expect(findPlaceholders(clean)).toEqual([]);
      expect(draft.headline).toBe(PLACEHOLDER); // no muta el original
    });

    it('normaliza las rutas de review_fields', () => {
      expect(reviewKey('skills[1].level')).toBe('skills.1.level');
    });
  });

  describe('compact', () => {
    it('quita opcionales vacíos pero conserva listas vacías y falsos', () => {
      expect(
        compact({
          phone: '',
          name: 'Ana',
          skills: [],
          ok: false,
          n: 0,
          loc: { city: '', country: 'AR' },
        }),
      ).toEqual({ name: 'Ana', skills: [], ok: false, n: 0, loc: { country: 'AR' } });
    });
  });

  describe('firstIncompleteStep', () => {
    it('devuelve el primer paso pendiente en orden', () => {
      expect(firstIncompleteStep(completion(false, false, false))).toBe('cv');
      expect(firstIncompleteStep(completion(true, false, true))).toBe('preferences');
      expect(firstIncompleteStep(completion(true, true, false))).toBe('privacy');
    });

    it('devuelve null con el perfil completo', () => {
      expect(firstIncompleteStep(completion(true, true, true))).toBeNull();
    });
  });

  describe('mergeDraft', () => {
    const profile = {
      personal: { name: '', email: 'ana@example.com' },
      summary: 'Resumen guardado',
      skills: [{ name: 'Git', level: 3 }],
    } as unknown as ProfileView;

    it('usa el borrador de la IA donde lo hay y lo guardado en el resto', () => {
      const merged = mergeDraft(profile, {
        personal: { name: 'Ana Ficticia', email: PLACEHOLDER },
        skills: [{ name: 'Python', level: 4 }],
      });
      expect(merged.personal).toEqual({ name: 'Ana Ficticia', email: 'ana@example.com' });
      expect(merged.skills).toEqual([{ name: 'Python', level: 4 }]);
      expect(merged.summary).toBe('Resumen guardado');
    });

    it('al reimportar un CV gana lo nuevo en título y resumen', () => {
      const saved = {
        ...profile,
        headline: 'Título viejo',
        languages: [{ name: 'Inglés', level: 'B2' }],
      } as unknown as ProfileView;
      const merged = mergeDraft(saved, {
        headline: 'Profesional IT · Desarrollo web',
        summary: 'Resumen nuevo del CV',
        personal: { name: PLACEHOLDER, email: 'nuevo@example.com' },
        languages: [],
      });
      expect(merged.headline).toBe('Profesional IT · Desarrollo web');
      expect(merged.summary).toBe('Resumen nuevo del CV');
      // Lo que el CV no trajo (marcado o lista vacía) conserva lo guardado.
      expect(merged.personal).toEqual({ name: '', email: 'nuevo@example.com' });
      expect(merged.languages).toEqual([{ name: 'Inglés', level: 'B2' }]);
    });

    it('un dato marcado para completar no pisa lo guardado', () => {
      const merged = mergeDraft(
        { ...profile, headline: 'Título guardado' } as unknown as ProfileView,
        { headline: PLACEHOLDER, summary: '' },
      );
      expect(merged.headline).toBe('Título guardado');
      expect(merged.summary).toBe('Resumen guardado');
    });

    it('sin borrador devuelve lo guardado', () => {
      expect(mergeDraft(profile, null).skills).toEqual([{ name: 'Git', level: 3 }]);
    });
  });
});

describe('fieldKeys (review_fields / suggested_fields)', () => {
  it('normaliza las rutas y tolera la lista ausente', () => {
    expect(fieldKeys(['headline', 'skills[1].level'])).toEqual(
      new Set(['headline', 'skills.1.level']),
    );
    expect(fieldKeys(undefined).size).toBe(0);
  });
});
