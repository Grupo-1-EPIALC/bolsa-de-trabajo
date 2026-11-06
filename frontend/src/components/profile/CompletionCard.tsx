import { STEP_LABEL } from '../../profile/labels';
import type { Completion } from '../../types/profile';

/** Forma común de la completitud de estudiantes y empresas (pasos distintos). */
type AnyCompletion<S extends string> = Omit<Completion, 'steps'> & {
  steps: Array<{
    step: S;
    complete: boolean;
    missing_required: number;
    missing_recommended: number;
  }>;
};

interface CompletionCardProps<S extends string> {
  completion: AnyCompletion<S>;
  onGoToStep?: (step: S) => void;
  compact?: boolean;
}

/** Completitud del perfil: la calcula profile-service por reglas (origin RULES). */
export function CompletionCard<S extends string>({
  completion,
  onGoToStep,
  compact,
}: CompletionCardProps<S>) {
  const required = completion.missing.filter((m) => m.required);
  return (
    <section className="card panel-rules" aria-labelledby="completion-title">
      <div className="card-body p-4">
        <div className="d-flex justify-content-between align-items-start gap-2 mb-3">
          <div>
            <span className="badge badge-rules text-uppercase mb-2">
              <i className="bi bi-shield-check me-1" aria-hidden="true" />
              Calculado por reglas
            </span>
            <h2 id="completion-title" className="h5 fw-bold mb-0">
              {completion.status === 'complete' ? 'Tu perfil está completo' : 'Completá tu perfil'}
            </h2>
          </div>
          <span className="score-value fs-2">{completion.percent}%</span>
        </div>
        <div
          className="progress mb-3"
          role="progressbar"
          aria-label="Avance del perfil"
          aria-valuenow={completion.percent}
          aria-valuemin={0}
          aria-valuemax={100}
          style={{ height: '0.6rem' }}
        >
          <div className="progress-bar bg-success" style={{ width: `${completion.percent}%` }} />
        </div>

        <ul className="list-unstyled d-grid gap-2 mb-0">
          {completion.steps.map((s) => (
            <li key={s.step} className="d-flex justify-content-between align-items-center gap-2">
              <span className="small fw-semibold">
                <i
                  className={`bi me-2 ${s.complete ? 'bi-check-circle-fill text-success' : 'bi-circle text-body-tertiary'}`}
                  aria-hidden="true"
                />
                {STEP_LABEL[s.step]}
                {!s.complete && s.missing_required > 0 && (
                  <span className="text-body-secondary fw-normal">
                    {' '}
                    · faltan {s.missing_required} obligatorio{s.missing_required > 1 ? 's' : ''}
                  </span>
                )}
              </span>
              {onGoToStep && (
                <button
                  type="button"
                  className="btn btn-sm btn-link p-0"
                  onClick={() => onGoToStep(s.step)}
                >
                  {s.complete ? 'Editar' : 'Completar'}
                </button>
              )}
            </li>
          ))}
        </ul>

        {!compact && required.length > 0 && (
          <div className="mt-3 small">
            <strong className="d-block mb-1">Te falta:</strong>
            <ul className="mb-0 ps-3">
              {required.slice(0, 6).map((m) => (
                <li key={m.field}>{m.message}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}
