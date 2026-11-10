import { describe, expect, it } from 'vitest';
import { matchedLabel, matchedReason, missingLabel, similarHint } from './skills';

describe('[UT-FE-SKL-01] Diccionario de competencias en la UI', () => {
  it('muestra qué skill del perfil cubre la pedida', () => {
    expect(matchedLabel({ skill: 'Python', via: null })).toBe('Python');
    expect(matchedLabel({ skill: 'SQL', via: 'PostgreSQL' })).toBe('SQL (por PostgreSQL)');
    expect(matchedReason({ skill: 'SQL', via: 'PostgreSQL', relation: 'implied' })).toBe(
      'PostgreSQL la cubre: cuenta como SQL',
    );
    expect(matchedReason({ skill: 'MySQL', via: 'MariaDB', relation: 'equivalent' })).toBe(
      'MariaDB equivale: cuenta como MySQL',
    );
    expect(matchedReason({ skill: 'Git', via: null, relation: 'exact' })).toBe('Tenés Git');
  });

  it('usa la herramienta similar como puente para aprender la que falta', () => {
    const gitlab = { skill: 'GitLab', current_level: 0, required_level: 2, similar_to: 'GitHub' };
    expect(missingLabel(gitlab)).toBe('GitLab (nivel 0 → 2 · similar a GitHub)');
    expect(missingLabel({ ...gitlab, similar_to: null })).toBe('GitLab (nivel 0 → 2)');
    expect(similarHint('GitLab', 'GitHub')).toBe(
      'Ya sabés GitHub: GitLab te va a resultar más fácil.',
    );
    expect(similarHint('GitLab', null)).toBe('');
  });
});
