import React, { useCallback, useEffect, useState } from 'react';
import { matchingService } from '../../services/matchingService';
import { jobsService } from '../../services/jobsService';
import { ApiError, errorMessage } from '../../services/api';
import { PRIORITY_CLASS, RuleMatch } from '../matching/RuleMatch';
import { useAiAnalysis } from '../matching/useAiAnalysis';
import { AiProgress } from '../matching/AiProgress';
import { dateLabel, placeLabel } from '../../jobs/format';
import { applicantsByProfile, rankByProfile } from '../../jobs/applications';
import { AVAILABILITY_START, WORK_MODALITY, labelOf } from '../../profile/labels';
import type {
  CompanyAIItem,
  CompanyRecommendationsView,
  CompanyRuleItem,
} from '../../types/matching';
import type { Applicant, JobOpportunity } from '../../types/jobs';

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

/** Contacto que el estudiante compartió al postularse. */
const ApplicantContactInfo: React.FC<{ applicant: Applicant }> = ({ applicant }) => {
  const { name, email, phone } = applicant.contact;
  return (
    <div className="small">
      <strong className="d-block">{name}</strong>
      <a className="d-inline-block me-3" href={`mailto:${email}`}>
        <i className="bi bi-envelope me-1" aria-hidden="true" />
        {email}
      </a>
      {phone && (
        <a className="d-inline-block" href={`tel:${phone.replace(/[^\d+]/g, '')}`}>
          <i className="bi bi-telephone me-1" aria-hidden="true" />
          {phone}
        </a>
      )}
    </div>
  );
};

const AppliedBadge: React.FC = () => (
  <span className="badge text-bg-success rounded-pill">
    <i className="bi bi-send-check me-1" aria-hidden="true" />
    Se postuló
  </span>
);

/** Todos los postulados a la búsqueda, con su contacto y su puesto en el ranking si lo tienen. */
const ApplicantsPanel: React.FC<{
  applicants: Applicant[] | null;
  error: string | null;
  ranking: Map<string, CompanyRuleItem>;
  onRetry: () => void;
}> = ({ applicants, error, ranking, onRetry }) => (
  <section className="card card-elevated" aria-labelledby="applicantsTitle">
    <div className="card-body p-4">
      <h3 className="h5 fw-bold mb-1" id="applicantsTitle">
        <i className="bi bi-send-check me-2" aria-hidden="true" />
        Postulados{applicants ? ` (${applicants.length})` : ''}
      </h3>
      <p className="small text-body-secondary mb-3">
        Se postularon a esta búsqueda y compartieron sus datos de contacto con tu empresa.
      </p>
      {error && (
        <div className="alert alert-warning d-flex justify-content-between align-items-center mb-0">
          <span>{error}</span>
          <button type="button" className="btn btn-sm btn-primary btn-pill" onClick={onRetry}>
            Reintentar
          </button>
        </div>
      )}
      {!error && !applicants && (
        <div className="text-center py-3">
          <span
            className="spinner-border spinner-border-sm text-primary"
            role="status"
            aria-label="Cargando postulados"
          />
        </div>
      )}
      {applicants && applicants.length === 0 && (
        <p className="small mb-0">Todavía nadie se postuló a esta búsqueda.</p>
      )}
      {applicants && applicants.length > 0 && (
        <ul className="list-group list-group-flush">
          {applicants.map((a) => {
            const ranked = ranking.get(a.profile_id);
            return (
              <li
                key={a.id}
                className="list-group-item px-0 d-flex flex-wrap justify-content-between gap-2"
              >
                <div>
                  <ApplicantContactInfo applicant={a} />
                  {a.headline && <span className="small d-block">{a.headline}</span>}
                </div>
                <div className="small text-md-end">
                  {ranked ? (
                    <span className="badge badge-rules d-inline-block mb-1">
                      Puesto {ranked.rank} · {Math.round(ranked.match.score)} puntos
                    </span>
                  ) : (
                    <span className="d-block text-body-secondary">
                      Fuera de los recomendados por reglas
                    </span>
                  )}
                  <span className="d-block text-body-secondary">
                    Se postuló el {dateLabel(a.applied_at)}
                  </span>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  </section>
);

const CandidateCard: React.FC<{
  item: CompanyRuleItem;
  ai?: CompanyAIItem;
  applicant?: Applicant;
}> = ({ item, ai, applicant }) => {
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
          <div className="flex-grow-1">
            <div className="d-flex flex-wrap justify-content-between gap-2">
              <h3 className="h6 fw-bold mb-1">{c.headline || `Candidato ${c.profile_id}`}</h3>
              {applicant && <AppliedBadge />}
            </div>
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
            {applicant && (
              <div className="border rounded-3 p-2 mt-2 bg-light">
                <ApplicantContactInfo applicant={applicant} />
              </div>
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
 * Candidatos para una búsqueda propia: los postulados con su contacto (contracts/jobs.md, A §12),
 * el ranking por reglas y, si se pide, el análisis de la IA (contracts/matching.md, A §4.2).
 * Los recomendados vienen sin nombre ni contacto, salvo los que se postularon.
 */
export const JobCandidates: React.FC<JobCandidatesProps> = ({ job, onBack }) => {
  const [view, setView] = useState<CompanyRecommendationsView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [applicants, setApplicants] = useState<Applicant[] | null>(null);
  const [applicantsError, setApplicantsError] = useState<string | null>(null);

  const loadApplicants = useCallback(async () => {
    setApplicantsError(null);
    try {
      setApplicants((await jobsService.applicants(job.id)).items);
    } catch (err) {
      setApplicantsError(errorMessage(err));
    }
  }, [job.id]);

  useEffect(() => {
    loadApplicants();
  }, [loadApplicants]);

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

  if (error || !view) {
    return (
      <div className="d-grid gap-4">
        {header}
        <ApplicantsPanel
          applicants={applicants}
          error={applicantsError}
          ranking={new Map()}
          onRetry={loadApplicants}
        />
        {error ? (
          <div className="alert alert-warning d-flex justify-content-between align-items-center">
            <span>{error}</span>
            <button type="button" className="btn btn-sm btn-primary btn-pill" onClick={load}>
              Reintentar
            </button>
          </div>
        ) : (
          <div className="text-center py-5">
            <span
              className="spinner-border text-primary"
              role="status"
              aria-label="Cargando candidatos"
            />
          </div>
        )}
      </div>
    );
  }

  const { rule_based: rules, ai_recommendations: aiBlock } = view;
  const aiById = new Map((aiBlock.items ?? []).map((i) => [i.profile_id, i]));
  const aiReady = aiBlock.status === 'ready' || aiBlock.status === 'completed';
  const appliedById = applicantsByProfile(applicants ?? []);

  return (
    <div className="d-grid gap-4">
      {header}
      <ApplicantsPanel
        applicants={applicants}
        error={applicantsError}
        ranking={rankByProfile(rules.items)}
        onRetry={loadApplicants}
      />
      <h3 className="h5 fw-bold mb-0">Recomendados por reglas</h3>
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
        {ai.busy && <AiProgress value={ai.progress} subject="recomendaciones de candidatos" />}
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
        . Para cuidar la equidad, el ranking no muestra nombres ni datos de contacto, salvo de
        quienes se postularon.
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
          applicant={appliedById.get(item.candidate.profile_id)}
        />
      ))}
    </div>
  );
};
