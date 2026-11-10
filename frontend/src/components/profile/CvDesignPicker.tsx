import React, { useCallback, useEffect, useId, useRef, useState } from 'react';
import { profileService } from '../../services/profileService';
import { errorMessage } from '../../services/api';
import {
  SOURCE_LABELS,
  aiAction,
  aiNote,
  describeOrder,
  isAiPending,
  layoutName,
} from '../../profile/cvDesign';
import type { CvDesignView, CvLayoutId } from '../../types/profile';

const POLL_MS = 3000;
const MAX_WAIT_MS = 3 * 60 * 1000;

interface CvDesignPickerProps {
  /** Cambia cuando se guarda el perfil: la elección por reglas puede cambiar. */
  profileVersion: number;
}

/**
 * "Diseño de tu CV": el estudiante elige uno de los diseños ATS-friendly del catálogo o deja
 * que decidan las reglas o la IA. El panel de reglas (verde) y el de IA (ámbar) van separados.
 */
export const CvDesignPicker: React.FC<CvDesignPickerProps> = ({ profileVersion }) => {
  const [view, setView] = useState<CvDesignView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [asking, setAsking] = useState(false);
  const timer = useRef<number | undefined>(undefined);
  const startedAt = useRef(0);
  const groupName = useId();

  const load = useCallback(async () => {
    try {
      setView(await profileService.getCvDesign());
    } catch (err) {
      setError(errorMessage(err));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load, profileVersion]);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  // Mientras la IA está eligiendo, consultar cada 3 s (hasta 3 min).
  useEffect(() => {
    window.clearTimeout(timer.current);
    if (!isAiPending(view)) {
      setAsking(false);
      startedAt.current = 0;
      return;
    }
    if (!startedAt.current) startedAt.current = Date.now();
    if (Date.now() - startedAt.current > MAX_WAIT_MS) {
      setAsking(false);
      setError('La IA está tardando demasiado. Probá de nuevo más tarde.');
      return;
    }
    timer.current = window.setTimeout(load, POLL_MS);
  }, [view, load]);

  const askAi = async () => {
    setError(null);
    setAsking(true);
    startedAt.current = Date.now();
    try {
      setView(await profileService.requestCvDesign());
    } catch (err) {
      setAsking(false);
      setError(errorMessage(err));
    }
  };

  const choose = async (layout: CvLayoutId | null) => {
    setError(null);
    setSaving(true);
    try {
      setView(await profileService.chooseCvDesign(layout));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  if (!view) {
    return (
      <div className="card card-elevated">
        <div className="card-body p-4">
          {error ? (
            <div className="alert alert-danger small mb-0" role="alert">
              {error}
            </div>
          ) : (
            <span
              className="spinner-border spinner-border-sm"
              role="status"
              aria-label="Cargando"
            />
          )}
        </div>
      </div>
    );
  }

  const ai = view.ai_recommendation;
  const note = aiNote(view);
  const pending = asking || isAiPending(view);

  return (
    <div className="card card-elevated">
      <div className="card-body p-4">
        <div className="d-flex flex-wrap justify-content-between align-items-start gap-2 mb-2">
          <div>
            <h2 className="section-title h5 mb-1">Diseño de tu CV</h2>
            <p className="small mb-0">
              Todos son de una columna, con texto real y títulos estándar, así los leen bien los
              sistemas de selección (ATS) y la IA. Sólo cambia qué secciones van primero.
            </p>
          </div>
          <span className="badge text-bg-light border" aria-live="polite">
            Ahora: <strong>{view.effective.name}</strong> · {SOURCE_LABELS[view.effective.source]}
          </span>
        </div>

        <fieldset className="mt-3" disabled={saving}>
          <legend className="visually-hidden">Elegí el diseño de tu CV</legend>
          <div className="row g-2">
            {view.catalog.map((layout) => {
              const id = `${groupName}-${layout.id}`;
              const active = view.effective.id === layout.id;
              return (
                <div className="col-md-4" key={layout.id}>
                  <input
                    type="radio"
                    className="btn-check"
                    name={groupName}
                    id={id}
                    checked={view.user_choice?.layout === layout.id}
                    onChange={() => choose(layout.id)}
                  />
                  <label
                    htmlFor={id}
                    className={`btn w-100 h-100 text-start p-3 ${active ? 'btn-outline-primary active' : 'btn-outline-secondary'}`}
                  >
                    <span className="d-block fw-bold">
                      {layout.name}
                      {active && <span className="badge text-bg-primary ms-2">Rige ahora</span>}
                    </span>
                    <span className="d-block small mt-1">{layout.best_for}</span>
                    <span className="d-block small text-body-secondary mt-1">
                      {describeOrder(layout.section_order)}
                    </span>
                  </label>
                </div>
              );
            })}
          </div>
        </fieldset>
        {view.user_choice && (
          <button
            type="button"
            className="btn btn-link btn-sm px-0 mt-2"
            onClick={() => choose(null)}
            disabled={saving}
          >
            Volver a la elección automática (reglas o IA)
          </button>
        )}

        {error && (
          <div className="alert alert-danger small mt-3 mb-0" role="alert">
            {error}
          </div>
        )}

        <div className="row g-3 mt-1">
          <div className="col-md-6">
            <div className="panel-rules rounded-3 p-3 h-100 small">
              <span className="badge badge-rules text-uppercase mb-2">
                <i className="bi bi-shield-check me-1" aria-hidden="true" />
                Calculado por reglas
              </span>
              <p className="mb-1">
                Recomienda <strong>{layoutName(view, view.rule_based.layout)}</strong>.
              </p>
              {view.rule_based.reasons.map((reason) => (
                <p className="mb-0" key={reason}>
                  {reason}
                </p>
              ))}
            </div>
          </div>
          <div className="col-md-6">
            <div className="panel-ai rounded-3 p-3 h-100 small" aria-live="polite">
              <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-2">
                <span className="badge badge-ai text-uppercase">
                  <i className="bi bi-stars me-1" aria-hidden="true" />
                  Sugerido por IA
                </span>
                <button
                  type="button"
                  className="btn btn-sm btn-primary btn-pill"
                  onClick={askAi}
                  disabled={pending}
                >
                  {pending && (
                    <span className="spinner-border spinner-border-sm me-1" aria-hidden="true" />
                  )}
                  {aiAction(view, asking)}
                </button>
              </div>
              {ai?.status === 'completed' && ai.layout ? (
                <>
                  <p className="mb-1">
                    Recomienda <strong>{layoutName(view, ai.layout)}</strong>
                    {ai.section_order.length > 0 && <>: {describeOrder(ai.section_order)}</>}.
                  </p>
                  {ai.rationale && <p className="mb-1">{ai.rationale}</p>}
                </>
              ) : (
                !pending && (
                  <p className="mb-1 text-body-secondary">
                    La IA mira un resumen de tu perfil, sin tus datos personales, y elige el diseño
                    que mejor muestra tus fortalezas.
                  </p>
                )
              )}
              {note && <p className="mb-1 text-warning-emphasis">{note}</p>}
              {ai?.disclaimer && <p className="mb-0 text-body-secondary">{ai.disclaimer}</p>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
