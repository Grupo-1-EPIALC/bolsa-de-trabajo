import React, { useCallback, useEffect, useState } from 'react';
import { matchingService } from '../../services/matchingService';
import { ApiError, errorMessage } from '../../services/api';
import { WORK_MODALITY, labelOf } from '../../profile/labels';
import { jobSteps } from '../../matching/training';
import { PRIORITY_CLASS, RuleMatch } from './RuleMatch';
import { useAiAnalysis } from './useAiAnalysis';
import { AiProgress } from './AiProgress';
import { TrainingAdvice } from './TrainingAdvice';
import { CompanyPublicProfileModal } from '../company/CompanyPublicProfileModal';
import type {
  StudentAIItem,
  StudentRecommendationsView,
  StudentRuleItem,
} from '../../types/matching';

interface JobRecommendationsProps {
  profileId: string;
  profileComplete: boolean;
  onCompleteProfile: () => void;
}

/** Bloque de IA de una oferta (origin AI): sin score. */
const AiAdvice: React.FC<{ item?: StudentAIItem }> = ({ item }) => {
  if (!item) return null;
  const { fit_reasons = [], watch_outs = [], priority } = item.content;
  const next_steps = jobSteps(item.content.next_steps);
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
  const [showCompanyModal, setShowCompanyModal] = useState(false);

  // Extraemos el company_id garantizando un string válido si viene en la respuesta
  const companyId = job.company_id || (job as any).companyId;

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
              {job.company_name && companyId ? (
                <button
                  type="button"
                  className="btn btn-link p-0 fw-bold me-2 text-decoration-none"
                  onClick={() => setShowCompanyModal(true)}
                  title="Ver perfil de la empresa"
                >
                  <i className="bi bi-building me-1" aria-hidden="true" />
                  {job.company_name}
                </button>
              ) : (
                job.company_name && <strong className="me-2">{job.company_name}</strong>
              )}
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
            <RuleMatch match={item.match} jobTitle={job.title} companyName={job.company_name} />
          </div>
          {ai && (
            <div className="col-lg-6">
              <AiAdvice item={ai} />
            </div>
          )}
        </div>
      </div>

      {/* Renderizado seguro del Modal Emergente */}
      {showCompanyModal && companyId && (
        <CompanyPublicProfileModal
          companyId={companyId}
          companyNameFallback={job.company_name}
          onClose={() => setShowCompanyModal(false)}
        />
      )}
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
  }, [load]);

  const {
    busy: aiBusy,
    error: aiError,
    request: requestAi,
    progress: aiProgress,
  } = useAiAnalysis(
    () => matchingService.requestStudentAnalysis(profileId),
    load,
    view?.ai_recommendations,
  );

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
        {aiBusy && <AiProgress value={aiProgress} subject="recomendaciones de ofertas" />}
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

      <TrainingAdvice profileId={profileId} />

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
