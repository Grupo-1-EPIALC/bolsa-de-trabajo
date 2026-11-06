import React, { useCallback, useEffect, useRef, useState } from 'react';
import { matchingService } from '../../services/matchingService';
import { ApiError, errorMessage } from '../../services/api';
import { WORK_MODALITY, labelOf } from '../../profile/labels';
import type {
  Match,
  StudentAIItem,
  StudentRecommendationsView,
  StudentRuleItem,
} from '../../types/matching';

interface JobRecommendationsProps {
  profileId: string;
  profileComplete: boolean;
  onCompleteProfile: () => void;
}

const POLL_MS = 3000;
const MAX_WAIT_MS = 5 * 60 * 1000;

const CRITERIA: Record<string, string> = {
  required_skills: 'Competencias obligatorias',
  desired_skills: 'Competencias deseables',
  levels: 'Niveles',
  experience: 'Experiencia',
  education: 'Formación',
  languages: 'Idiomas',
};

const PRIORITY_CLASS: Record<string, string> = {
  alta: 'text-bg-danger',
  media: 'text-bg-warning',
  baja: 'text-bg-light border',
};

/** Bloque por reglas de una oferta: score, desglose y skills (origin RULES). */
const RuleMatch: React.FC<{ match: Match }> = ({ match }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="panel-rules rounded-3 p-3 h-100">
      <div className="d-flex justify-content-between align-items-start gap-2 mb-2">
        <span className="badge badge-rules text-uppercase">
          <i className="bi bi-shield-check me-1" aria-hidden="true" />
          Calculado por reglas
        </span>
        <span className="score-value fs-3">
          {Math.round(match.score)}
          <span className="fs-6 fw-semibold text-body-secondary">/100</span>
        </span>
      </div>
      {match.excluding_cap_applied && (
        <p className="small text-danger-emphasis mb-2">
          <i className="bi bi-exclamation-triangle me-1" aria-hidden="true" />
          Te falta un requisito excluyente (puntaje máximo 40).
        </p>
      )}
      {match.matched_skills.length > 0 && (
        <div className="d-flex flex-wrap gap-1 mb-2">
          {match.matched_skills.map((s) => (
            <span key={s.skill} className="badge text-bg-success">
              <i className="bi bi-check me-1" aria-hidden="true" />
              {s.skill}
            </span>
          ))}
        </div>
      )}
      {match.missing_skills.length > 0 && (
        <div className="d-flex flex-wrap gap-1 mb-2">
          {match.missing_skills.map((s) => (
            <span key={s.skill} className="badge text-bg-light border">
              <i className="bi bi-x text-danger me-1" aria-hidden="true" />
              {s.skill} (nivel {s.current_level} → {s.required_level})
            </span>
          ))}
        </div>
      )}
      {match.conditions_fit && (
        <p className="small mb-2">
          <i
            className={`bi me-1 ${match.conditions_fit.compatible ? 'bi-check-circle text-success' : 'bi-x-circle text-danger'}`}
            aria-hidden="true"
          />
          Condiciones laborales {match.conditions_fit.compatible ? 'compatibles' : 'no compatibles'}
        </p>
      )}
      <button
        type="button"
        className="btn btn-sm btn-link p-0"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        {open ? 'Ocultar' : '¿Por qué este puntaje?'}
      </button>
      {open && (
        <div className="mt-2">
          {match.breakdown.map((b) => (
            <div key={b.criterion} className="mb-2">
              <div className="d-flex justify-content-between small">
                <span>{CRITERIA[b.criterion] ?? b.criterion}</span>
                <span className="fw-semibold">
                  {Math.round(b.earned * 10) / 10} / {b.weight}
                </span>
              </div>
              <div
                className="progress"
                role="progressbar"
                aria-label={CRITERIA[b.criterion] ?? b.criterion}
                aria-valuenow={b.earned}
                aria-valuemin={0}
                aria-valuemax={b.weight}
                style={{ height: '0.4rem' }}
              >
                <div
                  className="progress-bar bg-success"
                  style={{ width: `${b.weight ? (b.earned / b.weight) * 100 : 0}%` }}
                />
              </div>
            </div>
          ))}
          <p className="small text-body-secondary mb-0">Motor v{match.engine_version}</p>
        </div>
      )}
    </div>
  );
};

/** Bloque de IA de una oferta (origin AI): sin score. */
const AiAdvice: React.FC<{ item?: StudentAIItem }> = ({ item }) => {
  if (!item) return null;
  const { fit_reasons = [], watch_outs = [], next_steps = [], priority } = item.content;
  return (
    <div className="panel-ai rounded-3 p-3 h-100 small">
      <div className="d-flex justify-content-between align-items-center mb-2">
        <span className="badge badge-ai text-uppercase">
          <i className="bi bi-stars me-1" aria-hidden="true" />
          Sugerido por IA
        </span>
        {priority && (
          <span className={`badge ${PRIORITY_CLASS[priority]}`}>Prioridad {priority}</span>
        )}
      </div>
      {fit_reasons.length > 0 && (
        <>
          <strong>Por qué te conviene</strong>
          <ul className="ps-3 mb-2">
            {fit_reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </>
      )}
      {watch_outs.length > 0 && (
        <>
          <strong>A tener en cuenta</strong>
          <ul className="ps-3 mb-2">
            {watch_outs.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </>
      )}
      {next_steps.length > 0 && (
        <>
          <strong>Próximos pasos</strong>
          <ul className="ps-3 mb-0">
            {next_steps.map((s) => (
              <li key={s.text}>
                {s.text}
                {s.priority && (
                  <span className={`badge ms-1 ${PRIORITY_CLASS[s.priority]}`}>{s.priority}</span>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
};

const JobCard: React.FC<{ item: StudentRuleItem; ai?: StudentAIItem }> = ({ item, ai }) => {
  const { job } = item;
  const place = [job.location?.city, job.location?.province].filter(Boolean).join(', ');
  const modality = job.work_conditions?.work_modality ?? [];
  return (
    <article className="card card-elevated">
      <div className="card-body p-4">
        <div className="d-flex gap-3 align-items-start mb-3">
          <span className="step-number" aria-label={`Puesto ${item.rank} del ranking`}>
            {item.rank}
          </span>
          <div>
            <h3 className="h5 fw-bold mb-1">{job.title}</h3>
            <p className="small mb-0">
              {job.company_name && <strong className="me-2">{job.company_name}</strong>}
              {place && (
                <span className="me-2">
                  <i className="bi bi-geo-alt me-1" aria-hidden="true" />
                  {place}
                </span>
              )}
              {modality.map((m) => (
                <span
                  key={m}
                  className="badge bg-soft text-magenta border border-primary-subtle me-1"
                >
                  {labelOf(WORK_MODALITY, m)}
                </span>
              ))}
            </p>
          </div>
        </div>
        <div className="row g-3">
          <div className={ai ? 'col-lg-6' : 'col-12'}>
            <RuleMatch match={item.match} />
          </div>
          {ai && (
            <div className="col-lg-6">
              <AiAdvice item={ai} />
            </div>
          )}
        </div>
      </div>
    </article>
  );
};

export const JobRecommendations: React.FC<JobRecommendationsProps> = ({
  profileId,
  profileComplete,
  onCompleteProfile,
}) => {
  const [view, setView] = useState<StudentRecommendationsView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ApiError | Error | null>(null);
  const [aiBusy, setAiBusy] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);
  const timer = useRef<number | undefined>(undefined);

  const load = useCallback(async () => {
    setError(null);
    try {
      setView(await matchingService.getStudentRecommendations(profileId));
    } catch (err) {
      setError(err instanceof Error ? err : new Error(errorMessage(err)));
    } finally {
      setLoading(false);
    }
  }, [profileId]);

  useEffect(() => {
    load();
    return () => window.clearTimeout(timer.current);
  }, [load]);

  const poll = (requestId: string, startedAt: number) => {
    timer.current = window.setTimeout(async () => {
      try {
        const req = await matchingService.getRequest(requestId);
        if (req.status === 'completed') {
          setAiBusy(false);
          load();
        } else if (req.status === 'failed') {
          setAiBusy(false);
          setAiError(req.error?.message ?? 'La IA no pudo generar las recomendaciones.');
        } else if (Date.now() - startedAt > MAX_WAIT_MS) {
          setAiBusy(false);
          setAiError('El análisis está tardando demasiado. Probá de nuevo más tarde.');
        } else {
          poll(requestId, startedAt);
        }
      } catch (err) {
        setAiBusy(false);
        setAiError(errorMessage(err));
      }
    }, POLL_MS);
  };

  const requestAi = async () => {
    setAiBusy(true);
    setAiError(null);
    try {
      const req = await matchingService.requestStudentAnalysis(profileId);
      poll(req.request_id, Date.now());
    } catch (err) {
      setAiBusy(false);
      setAiError(errorMessage(err));
    }
  };

  // Si al entrar ya hay un pedido en curso, seguirlo.
  useEffect(() => {
    const ai = view?.ai_recommendations;
    if (!aiBusy && ai?.request_id && (ai.status === 'pending' || ai.status === 'processing')) {
      setAiBusy(true);
      poll(ai.request_id, Date.now());
    }
  }, [view]); // sólo al recibir una vista nueva

  if (loading) {
    return (
      <div className="text-center py-5">
        <span className="spinner-border text-primary" role="status" aria-label="Cargando ofertas" />
      </div>
    );
  }

  if (error) {
    const notInMatching = error instanceof ApiError && error.status === 404;
    return (
      <div className="card card-elevated mx-auto" style={{ maxWidth: '40rem' }}>
        <div className="card-body p-4 text-center">
          <span className="icon-circle mb-3">
            <i
              className={`bi ${notInMatching ? 'bi-hourglass-split' : 'bi-wifi-off'}`}
              aria-hidden="true"
            />
          </span>
          <h2 className="h5 fw-bold">
            {notInMatching
              ? 'Todavía no tenemos ofertas para vos'
              : 'No pudimos cargar las ofertas'}
          </h2>
          <p className="small">
            {notInMatching
              ? profileComplete
                ? 'Tu perfil todavía no entró al matching. Revisá que sea visible para empresas y que estés buscando trabajo.'
                : 'Las recomendaciones llegan cuando tu perfil está completo, visible y buscando trabajo.'
              : errorMessage(error)}
          </p>
          <div className="d-flex justify-content-center gap-2">
            {notInMatching ? (
              <button
                type="button"
                className="btn btn-primary btn-pill"
                onClick={onCompleteProfile}
              >
                {profileComplete ? 'Revisar privacidad' : 'Completar mi perfil'}
              </button>
            ) : (
              <button type="button" className="btn btn-primary btn-pill" onClick={load}>
                Reintentar
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (!view) return null;
  const { rule_based: rules, ai_recommendations: ai } = view;
  const aiByJob = new Map((ai.items ?? []).map((i) => [i.job_id, i]));
  const aiReady = ai.status === 'ready' || ai.status === 'completed';

  return (
    <div className="d-grid gap-4">
      {/* Estado de la IA */}
      <div className="panel-ai rounded-3 p-3 d-flex flex-wrap justify-content-between align-items-center gap-3">
        <div className="small">
          <span className="badge badge-ai text-uppercase me-2">
            <i className="bi bi-stars me-1" aria-hidden="true" />
            Sugerido por IA
          </span>
          {aiBusy && 'La IA está analizando tus ofertas…'}
          {!aiBusy && aiReady && (ai.summary || 'Consejos de la IA para cada oferta.')}
          {!aiBusy &&
            aiReady &&
            (ai.items ?? []).length === 0 &&
            ' La IA no encontró recomendaciones para agregar.'}
          {!aiBusy && ai.status === 'not_requested' && 'Pedile a la IA consejos para cada oferta.'}
          {!aiBusy && ai.status === 'failed' && (ai.error?.message ?? 'El último análisis falló.')}
          {aiError && <span className="text-danger-emphasis d-block mt-1">{aiError}</span>}
          {aiReady && ai.disclaimer && (
            <span className="d-block text-body-secondary mt-1">{ai.disclaimer}</span>
          )}
        </div>
        <button
          type="button"
          className="btn btn-sm btn-primary btn-pill"
          onClick={requestAi}
          disabled={aiBusy}
        >
          {aiBusy ? (
            <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />
          ) : (
            <i className="bi bi-stars me-2" aria-hidden="true" />
          )}
          {aiReady
            ? 'Actualizar consejos'
            : ai.status === 'failed'
              ? 'Reintentar'
              : 'Generar recomendaciones con IA'}
        </button>
      </div>

      <p className="small mb-0">
        Evaluamos {rules.evaluated} ofertas activas
        {rules.excluded_incompatible > 0 &&
          ` · ${rules.excluded_incompatible} no se muestran por condiciones incompatibles`}
        .
      </p>

      {rules.items.length === 0 ? (
        <div className="card card-elevated p-4 text-center">
          <p className="mb-0">
            No encontramos ofertas compatibles por ahora. Volvé a mirar pronto.
          </p>
        </div>
      ) : (
        rules.items.map((item) => (
          <JobCard key={item.job.job_id} item={item} ai={aiByJob.get(item.job.job_id)} />
        ))
      )}
    </div>
  );
};
