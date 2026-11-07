import React, { useCallback, useEffect, useState } from 'react';
import { matchingService } from '../../services/matchingService';
import { ApiError, errorMessage } from '../../services/api';
import { PRIORITY_CLASS, RuleMatch } from '../matching/RuleMatch';
import { useAiAnalysis } from '../matching/useAiAnalysis';
import { placeLabel } from '../../jobs/format';
import { AVAILABILITY_START, WORK_MODALITY, labelOf } from '../../profile/labels';
import type {
  CompanyAIItem,
  CompanyRecommendationsView,
  CompanyRuleItem,
} from '../../types/matching';
import type { JobOpportunity } from '../../types/jobs';

interface JobCandidatesProps {
  job: JobOpportunity;
  onBack: () => void;
}

/** "1,9 años de experiencia" (un decimal, es-AR). */
const yearsLabel = (years: number) => {
  const rounded = Math.round(years * 10) / 10;
  return `${rounded.toLocaleString('es-AR')} año${rounded === 1 ? '' : 's'} de experiencia`;
};

const Bullets: React.FC<{ title: string; items?: string[] }> = ({ title, items }) =>
  items && items.length > 0 ? (
    <>
      <strong>{title}</strong>
      <ul className="ps-3 mb-2">
        {items.map((i) => (
          <li key={i}>{i}</li>
        ))}
      </ul>
    </>
  ) : null;

/** Bloque de IA de un candidato (origin AI, badge ámbar): sin score. */
const AiCandidate: React.FC<{ item?: CompanyAIItem }> = ({ item }) => {
  if (!item) return null;
  const c = item.content;
  return (
    <div className="panel-ai rounded-3 p-3 h-100 small">
      <div className="d-flex justify-content-between align-items-center mb-2">
        <span className="badge badge-ai text-uppercase">
          <i className="bi bi-stars me-1" aria-hidden="true" />
          Sugerido por IA
        </span>
        {c.priority && (
          <span className={`badge ${PRIORITY_CLASS[c.priority]}`}>Prioridad {c.priority}</span>
        )}
      </div>
      {c.justification && <p className="mb-2">{c.justification}</p>}
      <Bullets title="Fortalezas" items={c.strengths} />
      <Bullets title="Brechas" items={c.gaps} />
      <Bullets title="Alertas de condiciones" items={c.conditions_alerts} />
      <Bullets title="Preguntas para la entrevista" items={c.interview_questions} />
    </div>
  );
};

const CandidateCard: React.FC<{ item: CompanyRuleItem; ai?: CompanyAIItem }> = ({ item, ai }) => {
  const c = item.candidate;
  const place = placeLabel(c.location ?? undefined);
  const modality = (c.work_conditions?.work_modality ?? [])
    .map((m) => labelOf(WORK_MODALITY, m))
    .join(' / ');
  const start = c.work_conditions?.availability_start;
  return (
    <article className="card card-elevated">
      <div className="card-body p-4">
        <div className="d-flex gap-3 align-items-start mb-3">
          <span className="step-number" aria-label={`Puesto ${item.rank} del ranking`}>
            {item.rank}
          </span>
          <div>
            <h3 className="h6 fw-bold mb-1">{c.headline || `Candidato ${c.profile_id}`}</h3>
            <p className="small mb-1">
              {[
                place,
                typeof c.years_experience === 'number' && yearsLabel(c.years_experience),
                c.academic_status?.career,
                modality,
                start && `Inicio: ${labelOf(AVAILABILITY_START, start).toLowerCase()}`,
              ]
                .filter(Boolean)
                .join(' · ')}
            </p>
            {(c.skills ?? []).length > 0 && (
              <p className="small mb-0 text-body-secondary">
                {c.skills!.map((s) => `${s.name} (${s.level})`).join(', ')}
              </p>
            )}
          </div>
        </div>
        <div className="row g-3">
          <div className={ai ? 'col-lg-6' : 'col-12'}>
            <RuleMatch match={item.match} viewer="company" />
          </div>
          {ai && (
            <div className="col-lg-6">
              <AiCandidate item={ai} />
            </div>
          )}
        </div>
      </div>
    </article>
  );
};

/**
 * Candidatos para una búsqueda propia (contracts/matching_frontend.md §4.2): ranking por reglas
 * y, si se pide, análisis de la IA. Los candidatos vienen sin nombre ni contacto, a propósito.
 */
export const JobCandidates: React.FC<JobCandidatesProps> = ({ job, onBack }) => {
  const [view, setView] = useState<CompanyRecommendationsView | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setView(await matchingService.getCompanyRecommendations(job.id));
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 404
          ? 'Esta búsqueda todavía no entró al matching.'
          : errorMessage(err),
      );
    }
  }, [job.id]);

  useEffect(() => {
    load();
  }, [load]);

  const ai = useAiAnalysis(
    () => matchingService.requestCompanyAnalysis(job.id),
    load,
    view?.ai_recommendations,
  );

  const header = (
    <div className="d-flex flex-wrap justify-content-between align-items-center gap-2">
      <div>
        <button type="button" className="btn btn-link btn-sm px-0" onClick={onBack}>
          <i className="bi bi-arrow-left me-1" aria-hidden="true" />
          Volver a la búsqueda
        </button>
        <h2 className="section-title h4 mb-0">Candidatos para "{job.title}"</h2>
      </div>
    </div>
  );

  if (error) {
    return (
      <div className="d-grid gap-3">
        {header}
        <div className="alert alert-warning d-flex justify-content-between align-items-center">
          <span>{error}</span>
          <button type="button" className="btn btn-sm btn-primary btn-pill" onClick={load}>
            Reintentar
          </button>
        </div>
      </div>
    );
  }
  if (!view) {
    return (
      <div className="d-grid gap-3">
        {header}
        <div className="text-center py-5">
          <span
            className="spinner-border text-primary"
            role="status"
            aria-label="Cargando candidatos"
          />
        </div>
      </div>
    );
  }

  const { rule_based: rules, ai_recommendations: aiBlock } = view;
  const aiById = new Map((aiBlock.items ?? []).map((i) => [i.profile_id, i]));
  const aiReady = aiBlock.status === 'ready' || aiBlock.status === 'completed';

  return (
    <div className="d-grid gap-4">
      {header}
      <div className="panel-ai rounded-3 p-3 d-flex flex-wrap justify-content-between align-items-center gap-3">
        <div className="small">
          <span className="badge badge-ai text-uppercase me-2">
            <i className="bi bi-stars me-1" aria-hidden="true" />
            Sugerido por IA
          </span>
          {ai.busy && 'La IA está analizando a los candidatos…'}
          {!ai.busy && aiReady && (aiBlock.summary || 'Análisis de la IA para cada candidato.')}
          {!ai.busy &&
            aiBlock.status === 'not_requested' &&
            'Pedile a la IA un análisis de cada candidato.'}
          {!ai.busy &&
            aiBlock.status === 'failed' &&
            (aiBlock.error?.message ?? 'El último análisis falló.')}
          {ai.error && <span className="text-danger-emphasis d-block mt-1">{ai.error}</span>}
          {aiReady && aiBlock.disclaimer && (
            <span className="d-block text-body-secondary mt-1">{aiBlock.disclaimer}</span>
          )}
        </div>
        <button
          type="button"
          className="btn btn-sm btn-primary btn-pill"
          onClick={ai.request}
          disabled={ai.busy || rules.items.length === 0}
        >
          {ai.busy ? (
            <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />
          ) : (
            <i className="bi bi-stars me-2" aria-hidden="true" />
          )}
          {aiReady ? 'Actualizar análisis' : 'Analizar con IA'}
        </button>
      </div>

      <p className="small mb-0">
        Evaluamos {rules.evaluated} perfiles buscables
        {rules.excluded_incompatible > 0 &&
          ` · ${rules.excluded_incompatible} no se muestran por condiciones incompatibles`}
        . Para cuidar la equidad, el ranking no muestra nombres ni datos de contacto.
      </p>
      {rules.items.length === 0 && (
        <div className="card card-elevated">
          <div className="card-body p-4 text-center small">
            Todavía no hay candidatos que cumplan los requisitos de esta búsqueda.
          </div>
        </div>
      )}
      {rules.items.map((item) => (
        <CandidateCard
          key={item.candidate.profile_id}
          item={item}
          ai={aiById.get(item.candidate.profile_id)}
        />
      ))}
    </div>
  );
};
