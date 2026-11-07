import React, { useState } from 'react';
import type { Match } from '../../types/matching';

export const CRITERIA: Record<string, string> = {
  required_skills: 'Competencias obligatorias',
  desired_skills: 'Competencias deseables',
  levels: 'Niveles',
  experience: 'Experiencia',
  education: 'Formación',
  languages: 'Idiomas',
};

export const PRIORITY_CLASS: Record<string, string> = {
  alta: 'text-bg-danger',
  media: 'text-bg-warning',
  baja: 'text-bg-light border',
};

interface RuleMatchProps {
  match: Match;
  /** Quién mira: cambia la persona de los textos ("te falta" / "le falta"). */
  viewer?: 'student' | 'company';
}

/** Bloque por reglas: score, desglose y skills (origin RULES, badge verde). */
export const RuleMatch: React.FC<RuleMatchProps> = ({ match, viewer = 'student' }) => {
  const [open, setOpen] = useState(false);
  const missingText =
    viewer === 'student'
      ? 'Te falta un requisito excluyente (puntaje máximo 40).'
      : 'Le falta un requisito excluyente (puntaje máximo 40).';
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
          {missingText}
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
