import React, { useCallback, useEffect, useState } from 'react';
import { matchingService } from '../../services/matchingService';
import { errorMessage } from '../../services/api';
import { labelOf } from '../../profile/labels';
import {
  TRAINING_ICONS,
  TRAINING_TYPES,
  describeGap,
  sortTraining,
  trainingAction,
  trainingType,
} from '../../matching/training';
import { AiProgress } from './AiProgress';
import { similarHint } from '../../matching/skills';
import { PRIORITY_CLASS } from './RuleMatch';
import { useAiAnalysis } from './useAiAnalysis';
import type { TrainingView } from '../../types/matching';

interface TrainingAdviceProps {
  profileId: string;
}

/**
 * "Qué sumar o mejorar": competencias que faltan en las ofertas más parecidas al perfil
 * (panel verde, por reglas) y cursos y consejos sugeridos por IA (panel ámbar). Es general,
 * no para una oferta.
 */
export const TrainingAdvice: React.FC<TrainingAdviceProps> = ({ profileId }) => {
  const [view, setView] = useState<TrainingView | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      setView(await matchingService.getTraining(profileId));
    } catch (err) {
      setLoadError(errorMessage(err));
    }
  }, [profileId]);

  useEffect(() => {
    load();
  }, [load]);

  const ai = view?.ai_recommendations;
  const analysis = useAiAnalysis(() => matchingService.requestTraining(profileId), load, ai);
  const items = sortTraining(ai?.items);
  const rules = view?.rule_based;
  const gaps = rules?.skill_gaps ?? [];
  const similar = rules?.similar_jobs.length ?? 0;

  return (
    <section className="card card-elevated" aria-labelledby="training-title">
      <div className="card-body p-4">
        <h2 id="training-title" className="h5 fw-bold mb-1">
          <i className="bi bi-lightbulb me-2" aria-hidden="true" />
          Qué sumar o mejorar
        </h2>
        <p className="small text-body-secondary mb-3">
          En general, según tu perfil y las ofertas activas más parecidas a él. No es para una
          oferta en particular.
        </p>

        {loadError && (
          <div className="alert alert-warning small d-flex justify-content-between align-items-center">
            <span>{loadError}</span>
            <button type="button" className="btn btn-sm btn-primary btn-pill" onClick={load}>
              Reintentar
            </button>
          </div>
        )}
        {!view && !loadError && (
          <span className="spinner-border spinner-border-sm" role="status" aria-label="Cargando" />
        )}

        {view && rules && (
          <div className="row g-3">
            <div className="col-lg-6">
              <div className="panel-rules rounded-3 p-3 h-100 small">
                <span className="badge badge-rules text-uppercase mb-2">
                  <i className="bi bi-calculator me-1" aria-hidden="true" />
                  Calculado por reglas
                </span>
                {gaps.length === 0 ? (
                  <p className="mb-0">
                    {similar > 0
                      ? 'Cumplís las competencias que piden las ofertas más parecidas a tu perfil.'
                      : 'Todavía no hay ofertas activas parecidas a tu perfil.'}
                  </p>
                ) : (
                  <ul className="list-unstyled d-grid gap-2 mb-0">
                    {gaps.map((gap) => (
                      <li key={gap.skill} className="d-flex flex-wrap gap-2 align-items-baseline">
                        <strong>{gap.skill}</strong>
                        <span className={`badge ${PRIORITY_CLASS[gap.priority] ?? ''}`}>
                          Prioridad {gap.priority}
                        </span>
                        <span className="w-100">{describeGap(gap, similar)}</span>
                        {gap.similar_to && (
                          <span className="w-100 text-success-emphasis">
                            <i className="bi bi-signpost-split me-1" aria-hidden="true" />
                            {similarHint(gap.skill, gap.similar_to)}
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            <div className="col-lg-6">
              <div className="panel-ai rounded-3 p-3 h-100 small">
                <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-2">
                  <span className="badge badge-ai text-uppercase">
                    <i className="bi bi-stars me-1" aria-hidden="true" />
                    Sugerido por IA
                  </span>
                  <button
                    type="button"
                    className="btn btn-sm btn-primary btn-pill"
                    onClick={analysis.request}
                    disabled={analysis.busy || gaps.length === 0}
                  >
                    {trainingAction(analysis.busy ? 'processing' : ai?.status, items.length > 0)}
                  </button>
                </div>

                {analysis.busy && (
                  <AiProgress value={analysis.progress} subject="qué sumar o mejorar" />
                )}
                {analysis.error && (
                  <div className="alert alert-danger small my-2">{analysis.error}</div>
                )}
                {!analysis.busy && ai?.status === 'failed' && !analysis.error && (
                  <p className="text-danger-emphasis mb-2">
                    {ai.error?.message ?? 'El último pedido falló.'}
                  </p>
                )}

                {!analysis.busy && ai?.summary && <p className="mb-2">{ai.summary}</p>}
                {!analysis.busy && items.length > 0 && (
                  <ul className="list-unstyled d-grid gap-2 mb-2" aria-live="polite">
                    {items.map((item) => {
                      const type = trainingType(item.type);
                      return (
                        <li key={`${type}-${item.skill}-${item.text}`} className="d-flex gap-2">
                          <i className={`bi ${TRAINING_ICONS[type]} mt-1`} aria-hidden="true" />
                          <div>
                            <div className="d-flex flex-wrap gap-1 mb-1">
                              <span className="badge text-bg-light border">
                                {labelOf(TRAINING_TYPES, type)}
                              </span>
                              {item.skill && (
                                <span className="badge text-bg-light border">{item.skill}</span>
                              )}
                              <span className={`badge ${PRIORITY_CLASS[item.priority] ?? ''}`}>
                                Prioridad {item.priority}
                              </span>
                            </div>
                            {item.text}
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                )}
                {!analysis.busy && items.length === 0 && ai?.status !== 'failed' && (
                  <p className="mb-2 text-body-secondary">
                    {gaps.length > 0
                      ? 'Pedile a la IA cursos y consejos para sumar o mejorar estas competencias.'
                      : 'No hace falta pedir sugerencias por ahora.'}
                  </p>
                )}
                {ai?.disclaimer && items.length > 0 && (
                  <p className="mb-0 text-body-secondary">{ai.disclaimer}</p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
};
