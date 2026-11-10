import { describe, expect, it } from 'vitest';
import { EXPECTED_AI_MS, estimateProgress, progressLabel } from './aiProgress';

describe('[UT-FE-PRG-01] Barra de progreso de la IA', () => {
  it('crece con el tiempo y nunca llega a 100 mientras corre', () => {
    const start = estimateProgress(0, 'processing');
    const mid = estimateProgress(EXPECTED_AI_MS, 'processing');
    const late = estimateProgress(EXPECTED_AI_MS * 20, 'processing');
    expect(start).toBe(5);
    expect(mid).toBeGreaterThan(start);
    expect(late).toBeGreaterThan(mid);
    expect(late).toBeLessThanOrEqual(95);
  });

  it('pending avanza poco y completed es 100', () => {
    expect(estimateProgress(EXPECTED_AI_MS * 5, 'pending')).toBeLessThanOrEqual(15);
    expect(estimateProgress(0, 'completed')).toBe(100);
    expect(estimateProgress(-1000, 'processing')).toBe(5);
  });

  it('texto de la etapa según el avance', () => {
    expect(progressLabel(5)).toBe('Enviando el pedido…');
    expect(progressLabel(30)).toBe('Buscando ofertas y competencias por reglas…');
    expect(progressLabel(60)).toBe('La IA está preparando las recomendaciones…');
    expect(progressLabel(90)).toBe('Verificando la respuesta…');
    expect(progressLabel(100)).toBe('Listo');
  });
});
