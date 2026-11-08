import React, { useCallback, useEffect, useId, useState } from 'react';
import { matchingService } from '../../services/matchingService';
import { errorMessage } from '../../services/api';
import { labelOf } from '../../profile/labels';
import {
  TRAINING_ICONS,
  TRAINING_TYPES,
  sortTraining,
  trainingAction,
} from '../../matching/training';
import { PRIORITY_CLASS } from './RuleMatch';
import { useAiAnalysis } from './useAiAnalysis';
import type { TrainingView } from '../../types/matching';

interface TrainingAdviceProps {
  profileId: string;
  jobId: string;
}

/**
 * "¿Cómo mejorar para esta oferta?": cursos, proyectos y consejos sugeridos por IA a partir de
 * las competencias que faltan según el motor de reglas. Panel ámbar, separado del puntaje.
 */
export const TrainingAdvice: React.FC<TrainingAdviceProps> = ({ profileId, jobId }) => {
  const [open, setOpen] = useState(false);
  const [view, setView] = useState<TrainingView | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const panelId = useId();

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      setView(await matchingService.getTraining(profileId, jobId));
    } catch (err) {
      setLoadError(errorMessage(err));
    }
  }, [profileId, jobId]);

  useEffect(() => {
    if (open && !view) load();
  }, [open, view, load]);

  const ai = view?.ai_recommendations;
  const analysis = useAiAnalysis(() => matchingService.requestTraining(profileId, jobId), load, ai);
  const items = sortTraining(ai?.items);
  const missing = view?.rule_based.missing_skills ?? [];

  return (
    <div className="mt-3">
      <button
        type="button"
        className="btn btn-sm btn-outline-primary btn-pill"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((v) => !v)}
      >
        <i className={`bi ${open ? 'bi-chevron-up' : 'bi-lightbulb'} me-1`} aria-hidden="true" />
        ¿Cómo mejorar para esta oferta?
      </button>

      {open && (
        <div id={panelId} className="panel-ai rounded-3 p-3 mt-2 small">
          <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-2">
            <span className="badge badge-ai text-uppercase">
              <i className="bi bi-stars me-1" aria-hidden="true" />
              Sugerido por IA
            </span>
            {view && (
              <button
                type="button"
                className="btn btn-sm btn-primary btn-pill"
                onClick={analysis.request}
                disabled={analysis.busy}
              >
                {analysis.busy && (
                  <span className="spinner-border spinner-border-sm me-1" aria-hidden="true" />
                )}
                {trainingAction(analysis.busy ? 'processing' : ai?.status, items.length > 0)}
              </button>
            )}
          </div>

          {loadError && <div className="alert alert-danger small mb-2">{loadError}</div>}
          {analysis.error && <div className="alert alert-danger small mb-2">{analysis.error}</div>}
          {!view && !loadError && (
            <span
              className="spinner-border spinner-border-sm"
              role="status"
              aria-label="Cargando"
            />
          )}

          {view && (
            <>
              <p className="mb-2">
                {missing.length > 0 ? (
                  <>
                    Según el motor de reglas te falta o podés reforzar:{' '}
                    <strong>{missing.map((m) => m.skill).join(', ')}</strong>.
                  </>
                ) : (
                  'Según el motor de reglas cumplís todas las competencias que pide la oferta.'
                )}
              </p>

              {items.length > 0 ? (
                <ul className="list-unstyled d-grid gap-2 mb-2" aria-live="polite">
                  {items.map((item) => (
                    <li key={`${item.type}-${item.skill}-${item.text}`} className="d-flex gap-2">
                      <i
                        className={`bi ${TRAINING_ICONS[item.type] ?? 'bi-dot'} mt-1`}
                        aria-hidden="true"
                      />
                      <div>
                        <div className="d-flex flex-wrap gap-1 mb-1">
                          <span className="badge text-bg-light border">
                            {labelOf(TRAINING_TYPES, item.type)}
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
                  ))}
                </ul>
              ) : (
                !analysis.busy && (
                  <p className="mb-2 text-body-secondary">
                    Pedile a la IA cursos, proyectos y consejos para cubrir lo que falta.
                  </p>
                )
              )}

              {ai?.disclaimer && <p className="mb-0 text-body-secondary">{ai.disclaimer}</p>}
            </>
          )}
        </div>
      )}
    </div>
  );
};
