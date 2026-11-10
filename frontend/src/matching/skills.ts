// Cómo mostrar las competencias según el diccionario del motor de reglas
// (contracts/matching.md, parte A §5.1): alias, implicaciones, equivalentes y similares.
import type { MatchedSkill, MissingSkill } from '../types/matching';

const RELATION_TEXT: Record<string, string> = {
  implied: 'la cubre',
  equivalent: 'equivale',
};

/** "SQL" o "SQL (por PostgreSQL)" si la cubre otra skill del perfil. */
export function matchedLabel(skill: Pick<MatchedSkill, 'skill' | 'via'>): string {
  return skill.via ? `${skill.skill} (por ${skill.via})` : skill.skill;
}

/** Texto para lectores de pantalla y `title`: por qué cuenta como cubierta. */
export function matchedReason(skill: Pick<MatchedSkill, 'skill' | 'via' | 'relation'>): string {
  if (!skill.via) return `Tenés ${skill.skill}`;
  const how = RELATION_TEXT[skill.relation ?? ''] ?? 'la cubre';
  return `${skill.via} ${how}: cuenta como ${skill.skill}`;
}

/** "Ya sabés GitHub: GitLab te va a resultar más fácil." */
export function similarHint(skill: string, similarTo?: string | null): string {
  return similarTo ? `Ya sabés ${similarTo}: ${skill} te va a resultar más fácil.` : '';
}

/** Faltante con la similar como puente: "GitLab (nivel 0 → 2 · similar a GitHub)". */
export function missingLabel(
  skill: Pick<MissingSkill, 'skill' | 'current_level' | 'required_level' | 'similar_to'>,
): string {
  const levels = `nivel ${skill.current_level} → ${skill.required_level}`;
  return skill.similar_to
    ? `${skill.skill} (${levels} · similar a ${skill.similar_to})`
    : `${skill.skill} (${levels})`;
}
