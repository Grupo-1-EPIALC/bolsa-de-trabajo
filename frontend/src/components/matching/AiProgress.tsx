import React from 'react';
import { progressLabel } from '../../matching/aiProgress';

interface AiProgressProps {
  /** Porcentaje estimado (0–100) que devuelve `useAiAnalysis`. */
  value: number;
  /** Qué se está buscando, para lectores de pantalla ("recomendaciones de ofertas"). */
  subject: string;
}

/** Barra de progreso mientras la IA genera recomendaciones (el avance es estimado). */
export const AiProgress: React.FC<AiProgressProps> = ({ value, subject }) => {
  const percent = Math.max(0, Math.min(100, Math.round(value)));
  const label = progressLabel(percent);
  return (
    <div className="w-100 mt-2">
      <div className="d-flex justify-content-between small mb-1" aria-hidden="true">
        <span>{label}</span>
        <span>{percent} %</span>
      </div>
      <div
        className="progress"
        role="progressbar"
        aria-label={`Buscando ${subject}`}
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuetext={`${percent} %: ${label}`}
        style={{ height: '0.5rem' }}
      >
        <div
          className="progress-bar progress-bar-striped progress-bar-animated"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
};
