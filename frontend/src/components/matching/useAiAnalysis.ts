import { useCallback, useEffect, useRef, useState } from 'react';
import { matchingService } from '../../services/matchingService';
import { errorMessage } from '../../services/api';
import type { AIBlock, RecommendationRequest } from '../../types/matching';

const POLL_MS = 3000;
const MAX_WAIT_MS = 5 * 60 * 1000;

/**
 * Pedido de análisis con IA (WF-06) y seguimiento hasta que termina (§3.1 de matching_frontend).
 * `start` crea el pedido; al completarse se llama `onCompleted` para recargar la vista.
 * Si la vista ya trae un pedido en curso (`ai.request_id`), lo sigue solo.
 */
export function useAiAnalysis(
  start: () => Promise<RecommendationRequest>,
  onCompleted: () => void,
  ai: AIBlock<unknown> | undefined,
) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  const poll = useCallback(
    (requestId: string, startedAt: number) => {
      timer.current = window.setTimeout(async () => {
        try {
          const req = await matchingService.getRequest(requestId);
          if (req.status === 'completed') {
            setBusy(false);
            onCompleted();
          } else if (req.status === 'failed') {
            setBusy(false);
            setError(req.error?.message ?? 'La IA no pudo generar las recomendaciones.');
          } else if (Date.now() - startedAt > MAX_WAIT_MS) {
            setBusy(false);
            setError('El análisis está tardando demasiado. Probá de nuevo más tarde.');
          } else {
            poll(requestId, startedAt);
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
    setBusy(true);
    setError(null);
    try {
      const req = await start();
      poll(req.request_id, Date.now());
    } catch (err) {
      setBusy(false);
      setError(errorMessage(err));
    }
  };

  // Si al entrar ya hay un pedido en curso, seguirlo.
  useEffect(() => {
    if (!busy && ai?.request_id && (ai.status === 'pending' || ai.status === 'processing')) {
      setBusy(true);
      poll(ai.request_id, Date.now());
    }
  }, [ai]); // sólo al recibir una vista nueva

  return { busy, error, request };
}
