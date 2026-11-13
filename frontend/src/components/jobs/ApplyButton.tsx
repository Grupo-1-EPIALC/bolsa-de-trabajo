import React from 'react';
import { SHARED_DATA_NOTE } from '../../jobs/applications';
import type { ApplicationControls } from './useApplications';

interface ApplyButtonProps {
  jobId: string;
  jobTitle: string;
  controls: ApplicationControls;
  /** Muestra debajo qué datos ve la empresa (en el detalle y en las tarjetas grandes). */
  showNote?: boolean;
}

/** "Postularme" / "Retirar postulación" de un estudiante sobre una oferta. */
export const ApplyButton: React.FC<ApplyButtonProps> = ({
  jobId,
  jobTitle,
  controls,
  showNote = true,
}) => {
  const applied = controls.isApplied(jobId);
  const busy = controls.isBusy(jobId);
  const error = controls.errorFor(jobId);
  const spinner = <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />;

  return (
    <div className="d-flex flex-column align-items-start align-items-md-end gap-1">
      <div className="d-flex flex-wrap align-items-center gap-2">
        {applied && (
          <span className="badge text-bg-success rounded-pill">
            <i className="bi bi-check2-circle me-1" aria-hidden="true" />
            Te postulaste
          </span>
        )}
        {applied ? (
          <button
            type="button"
            className="btn btn-sm btn-outline-secondary btn-pill"
            onClick={() => controls.withdraw(jobId)}
            disabled={busy}
            aria-label={`Retirar la postulación a ${jobTitle}`}
          >
            {busy ? spinner : <i className="bi bi-x-circle me-2" aria-hidden="true" />}
            Retirar postulación
          </button>
        ) : (
          <button
            type="button"
            className="btn btn-sm btn-primary btn-pill"
            onClick={() => controls.apply(jobId)}
            disabled={busy}
            aria-label={`Postularme a ${jobTitle}`}
            title={SHARED_DATA_NOTE}
          >
            {busy ? spinner : <i className="bi bi-send me-2" aria-hidden="true" />}
            Postularme
          </button>
        )}
      </div>
      {showNote && !applied && (
        <span className="small text-body-secondary">{SHARED_DATA_NOTE}</span>
      )}
      {error && (
        <span className="small text-danger-emphasis" role="alert">
          {error}
        </span>
      )}
    </div>
  );
};
