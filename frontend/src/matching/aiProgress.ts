// Barra de progreso mientras la IA (WF-06) genera recomendaciones.
// El backend no informa un porcentaje real: se estima con el tiempo transcurrido y el estado
// del pedido, sin llegar nunca a 100 % hasta que el pedido termina.

/** Duración típica de un análisis con IA (ms). Con ese tiempo la barra ronda el 60 %. */
export const EXPECTED_AI_MS = 40_000;

const MAX_WHILE_RUNNING = 95;

export type AiRequestStatus = 'pending' | 'processing' | 'completed' | 'failed' | undefined;

/** Porcentaje estimado (0–100). `completed` es 100; mientras corre, crece y frena antes de 95. */
export function estimateProgress(
  elapsedMs: number,
  status: AiRequestStatus,
  expectedMs: number = EXPECTED_AI_MS,
): number {
  if (status === 'completed') return 100;
  const t = Math.max(0, elapsedMs);
  const curve = 1 - Math.exp(-t / Math.max(1, expectedMs));
  // `pending`: el pedido todavía no llegó a n8n, la barra avanza poco.
  const ceiling = status === 'pending' ? 15 : MAX_WHILE_RUNNING;
  const value = 5 + (MAX_WHILE_RUNNING - 5) * curve;
  return Math.round(Math.min(ceiling, value));
}

/** Texto de la etapa según el avance estimado. */
export function progressLabel(percent: number): string {
  if (percent >= 100) return 'Listo';
  if (percent < 15) return 'Enviando el pedido…';
  if (percent < 45) return 'Buscando ofertas y competencias por reglas…';
  if (percent < 80) return 'La IA está preparando las recomendaciones…';
  return 'Verificando la respuesta…';
}
