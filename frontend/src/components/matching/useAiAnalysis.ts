import { useCallback, useEffect, useRef, useState } from 'react';
import { matchingService } from '../../services/matchingService';
import { errorMessage } from '../../services/api';
import { estimateProgress, type AiRequestStatus } from '../../matching/aiProgress';
import type { AIBlock, RecommendationRequest } from '../../types/matching';

const POLL_MS = 3000;
const TICK_MS = 500;
const MAX_WAIT_MS = 5 * 60 * 1000;

/**
 * Pedido de análisis con IA (WF-06) y seguimiento hasta que termina (§3.1 de matching_frontend).
 * `start` crea el pedido; al completarse se llama `onCompleted` para recargar la vista.
 * Si la vista ya trae un pedido en curso (`ai.request_id`), lo sigue solo.
 * `progress` (0–100) es una estimación para la barra de progreso mientras espera.
 */
export function useAiAnalysis(
  start: () => Promise<RecommendationRequest>,
  onCompleted: () => void,
  ai: AIBlock<unknown> | undefined,
) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<AiRequestStatus>(undefined);
  const [startedAt, setStartedAt] = useState(0);
  const [now, setNow] = useState(0);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  // Reloj de la barra: sólo corre mientras hay un pedido en curso.
  useEffect(() => {
    if (!busy) return undefined;
    setNow(Date.now());
    const id = window.setInterval(() => setNow(Date.now()), TICK_MS);
    return () => window.clearInterval(id);
  }, [busy]);

  const begin = (initial: AiRequestStatus) => {
    const t = Date.now();
    setStartedAt(t);
    setNow(t);
    setStatus(initial);
    setBusy(true);
  };

  const poll = useCallback(
    (requestId: string, since: number) => {
      timer.current = window.setTimeout(async () => {
        try {
          const req = await matchingService.getRequest(requestId);
          setStatus(req.status);
          if (req.status === 'completed') {
            setBusy(false);
            onCompleted();
          } else if (req.status === 'failed') {
            setBusy(false);
            setError(req.error?.message ?? 'La IA no pudo generar las recomendaciones.');
          } else if (Date.now() - since > MAX_WAIT_MS) {
            setBusy(false);
            setError('El análisis está tardando demasiado. Probá de nuevo más tarde.');
          } else {
            poll(requestId, since);
          }
        } catch (err) {
          setBusy(false);
          setError(errorMessage(err));
        }
      }, POLL_MS);
    },
    [onCompleted],
  );

  const request = async () => {
    begin('pending');
    setError(null);
    try {
      const req = await start();
      setStatus(req.status);
      poll(req.request_id, Date.now());
    } catch (err) {
      setBusy(false);
      setError(errorMessage(err));
    }
  };

  // Si al entrar ya hay un pedido en curso, seguirlo.
  useEffect(() => {
    if (!busy && ai?.request_id && (ai.status === 'pending' || ai.status === 'processing')) {
      begin(ai.status);
      poll(ai.request_id, Date.now());
    }
  }, [ai]); // sólo al recibir una vista nueva

  const progress = busy ? estimateProgress(now - startedAt, status) : 0;
  return { busy, error, request, progress };
}
