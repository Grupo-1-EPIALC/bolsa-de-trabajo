import React from 'react';
import type { Match } from '../../types/matching';
import { CRITERIA, PRIORITY_CLASS } from './RuleMatch';
import { matchedLabel, matchedReason, missingLabel } from '../../matching/skills';

interface RuleScoreModalProps {
  match: Match;
  jobTitle?: string;
  companyName?: string;
  onClose: () => void;
}

export const RuleScoreModal: React.FC<RuleScoreModalProps> = ({
  match,
  jobTitle,
  companyName,
  onClose,
}) => {
  return (
    <div
      className="modal fade show d-block"
      tabIndex={-1}
      role="dialog"
      aria-labelledby="ruleScoreModalTitle"
      aria-modal="true"
      style={{ backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1055 }}
    >
      <div className="modal-dialog modal-dialog-centered modal-lg" role="document">
        <div className="modal-content border-0 shadow-lg">
          {/* Cabecera */}
          <div className="modal-header border-bottom-0 pb-0">
            <div>
              <span className="badge badge-rules text-uppercase mb-2">
                <i className="bi bi-shield-check me-1" aria-hidden="true" />
                Calculado por reglas
              </span>
              <h2 className="modal-title h4 fw-bold" id="ruleScoreModalTitle">
                Desglose del Puntaje de Compatibilidad
              </h2>
              {jobTitle && (
                <p className="text-body-secondary small mb-0">
                  {jobTitle} {companyName ? `· ${companyName}` : ''}
                </p>
              )}
            </div>
            <button
              type="button"
              className="btn-close"
              aria-label="Cerrar modal"
              onClick={onClose}
            />
          </div>

          <div className="modal-body p-4">
            {/* Score Principal */}
            <div className="d-flex align-items-center justify-content-between p-3 rounded-3 bg-light mb-4">
              <div>
                <span className="d-block text-uppercase text-body-secondary small fw-bold">
                  Puntaje Total
                </span>
                <span className="score-value fs-1 fw-bold text-success">
                  {Math.round(match.score)}
                  <span className="fs-5 text-body-secondary"> / 100</span>
                </span>
              </div>
              <div className="text-end">
                <span className="badge text-bg-secondary">Motor v{match.engine_version}</span>
                {match.rules_version && (
                  <span className="d-block text-body-secondary small mt-1">
                    Reglas v{match.rules_version}
                  </span>
                )}
              </div>
            </div>

            {/* Alerta de Tope Excluyente */}
            {match.excluding_cap_applied && (
              <div className="alert alert-danger d-flex align-items-center gap-2 mb-4" role="alert">
                <i className="bi bi-exclamation-triangle-fill fs-4 flex-shrink-0" />
                <div className="small">
                  <strong>Requisito excluyente no cumplido:</strong> Tu perfil no satisface una
                  competencia marcada como obligatoria/excluyente. Por regla del motor, el score
                  máximo posible se topeó en 40 puntos.
                </div>
              </div>
            )}

            {/* Evaluacion por Criterios */}
            <section className="mb-4">
              <h3 className="h6 fw-bold mb-3">Evaluación por Criterios</h3>
              <div className="d-grid gap-3">
                {match.breakdown.map((b) => {
                  const percent = b.weight > 0 ? (b.earned / b.weight) * 100 : 0;
                  return (
                    <div key={b.criterion}>
                      <div className="d-flex justify-content-between align-items-center small mb-1">
                        <span className="fw-semibold">{CRITERIA[b.criterion] ?? b.criterion}</span>
                        <span className="fw-bold">
                          {Math.round(b.earned * 10) / 10} / {b.weight} pts
                        </span>
                      </div>
                      <div
                        className="progress"
                        role="progressbar"
                        aria-label={CRITERIA[b.criterion] ?? b.criterion}
                        aria-valuenow={b.earned}
                        aria-valuemin={0}
                        aria-valuemax={b.weight}
                        style={{ height: '0.5rem' }}
                      >
                        <div className="progress-bar bg-success" style={{ width: `${percent}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>

            {/* Skills Coincidentes y Faltantes */}
            <div className="row g-3 mb-4">
              <div className="col-md-6">
                <div className="border rounded-3 p-3 h-100 bg-white">
                  <h4 className="h6 fw-bold text-success mb-2">
                    <i className="bi bi-check-circle me-1" />
                    Competencias Coincidentes ({match.matched_skills.length})
                  </h4>
                  {match.matched_skills.length === 0 ? (
                    <p className="small text-body-secondary mb-0">Sin coincidencias registradas.</p>
                  ) : (
                    <div className="d-flex flex-wrap gap-1">
                      {match.matched_skills.map((s) => (
                        <span
                          key={s.skill}
                          className="badge text-bg-success small"
                          title={matchedReason(s)}
                        >
                          {matchedLabel(s)} (Nivel {s.profile_level})
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div className="col-md-6">
                <div className="border rounded-3 p-3 h-100 bg-white">
                  <h4 className="h6 fw-bold text-danger mb-2">
                    <i className="bi bi-x-circle me-1" />
                    Competencias a Reforzar ({match.missing_skills.length})
                  </h4>
                  {match.missing_skills.length === 0 ? (
                    <p className="small text-body-secondary mb-0">
                      ¡Cumplís todos los requisitos de la oferta!
                    </p>
                  ) : (
                    <div className="d-flex flex-wrap gap-1">
                      {match.missing_skills.map((s) => (
                        <span
                          key={s.skill}
                          className={`badge ${PRIORITY_CLASS[s.priority] || 'text-bg-light border'} small`}
                        >
                          {missingLabel(s)}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Condiciones Laborales */}
            {match.conditions_fit && (
              <section className="border-top pt-3">
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <h3 className="h6 fw-bold mb-0">Compatibilidad de Condiciones Laborales</h3>
                  <span className="badge text-bg-light border text-body-secondary">
                    Pesa poco en el score (7 de 100)
                  </span>
                </div>
                <div className="p-3 rounded-3 bg-light">
                  <p className="small mb-0">
                    <i
                      className={`bi me-2 fs-6 ${
                        match.conditions_fit.compatible
                          ? 'bi-check-circle-fill text-success'
                          : 'bi-exclamation-circle-fill text-warning'
                      }`}
                    />
                    <strong>Estado:</strong>{' '}
                    {match.conditions_fit.compatible
                      ? 'Condiciones compatibles'
                      : 'Incompatibilidades encontradas'}
                  </p>
                </div>
              </section>
            )}
          </div>

          <div className="modal-footer border-top-0">
            <button type="button" className="btn btn-secondary btn-pill" onClick={onClose}>
              Cerrar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
