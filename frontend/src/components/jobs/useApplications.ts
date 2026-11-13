import { useCallback, useEffect, useState } from 'react';
import { jobsService } from '../../services/jobsService';
import { appliedJobIds, applicationErrorMessage } from '../../jobs/applications';

export interface ApplicationControls {
  isApplied: (jobId: string) => boolean;
  isBusy: (jobId: string) => boolean;
  errorFor: (jobId: string) => string | undefined;
  apply: (jobId: string) => Promise<void>;
  withdraw: (jobId: string) => Promise<void>;
}

/**
 * Postulaciones del estudiante: carga a qué ofertas se postuló y permite postularse o retirarse.
 * Con `enabled = false` (otros roles) no consulta nada y no hay ofertas postuladas.
 */
export function useApplications(enabled = true): ApplicationControls {
  const [applied, setApplied] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!enabled) return;
    let active = true;
    jobsService
      .myApplications()
      .then((list) => {
        if (active) setApplied(appliedJobIds(list));
      })
      // Si falla, los botones siguen andando: postularse es idempotente.
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [enabled]);

  const run = useCallback(
    async (jobId: string, action: () => Promise<unknown>, nowApplied: boolean) => {
      setBusy(jobId);
      setErrors((current) => {
        const next = { ...current };
        delete next[jobId];
        return next;
      });
      try {
        await action();
        setApplied((current) => {
          const next = new Set(current);
          if (nowApplied) next.add(jobId);
          else next.delete(jobId);
          return next;
        });
      } catch (err) {
        setErrors((current) => ({
          ...current,
          [jobId]: applicationErrorMessage(err),
        }));
      } finally {
        setBusy(null);
      }
    },
    [],
  );

  return {
    isApplied: (jobId) => applied.has(jobId),
    isBusy: (jobId) => busy === jobId,
    errorFor: (jobId) => errors[jobId],
    apply: (jobId) => run(jobId, () => jobsService.apply(jobId), true),
    withdraw: (jobId) => run(jobId, () => jobsService.withdraw(jobId), false),
  };
}
