import React, { useEffect, useRef, useState } from 'react';
import { profileService, validateCvFile } from '../../services/profileService';
import { errorMessage } from '../../services/api';
import type { CvJob, CvResult } from '../../types/profile';

interface CvImportProps {
  onCompleted: (result: CvResult) => void;
  onManual: () => void;
  onCancel: () => void;
}

const POLL_MS = 1500;
const MAX_WAIT_MS = 4 * 60 * 1000;

/** Sube el CV y sigue la extracción con IA (polling cada 1,5 s, contrato §6). */
export const CvImport: React.FC<CvImportProps> = ({ onCompleted, onManual, onCancel }) => {
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState<CvJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  const poll = (jobId: string, startedAt: number) => {
    timer.current = window.setTimeout(async () => {
      try {
        const current = await profileService.getCvJob(jobId);
        setJob(current);
        if (current.status === 'completed' && current.result) {
          onCompleted(current.result);
        } else if (current.status === 'failed') {
          setError(current.error?.message ?? 'No pudimos procesar el CV.');
        } else if (Date.now() - startedAt > MAX_WAIT_MS) {
          setError('El análisis está tardando demasiado. Probá de nuevo en unos minutos.');
        } else {
          poll(jobId, startedAt);
        }
      } catch (err) {
        setError(errorMessage(err));
      }
    }, POLL_MS);
  };

  const pick = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0] ?? null;
    setError(selected ? validateCvFile(selected) : null);
    setFile(selected && !validateCvFile(selected) ? selected : null);
  };

  const upload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const started = await profileService.uploadCv(file);
      setJob(started);
      poll(started.job_id, Date.now());
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setUploading(false);
    }
  };

  const reset = () => {
    window.clearTimeout(timer.current);
    setJob(null);
    setFile(null);
    setError(null);
  };

  const processing = job?.status === 'processing' && !error;
  const progress = Math.max(5, Math.min(100, job?.progress_percent ?? 5));

  return (
    <div className="card card-elevated mx-auto" style={{ maxWidth: '44rem' }}>
      <div className="card-body p-4 p-md-5">
        <h2 className="h4 fw-bold mb-1">Importar datos desde tu CV</h2>
        <p className="small mb-4">
          La IA sólo sugiere: nada se guarda en tu perfil hasta que lo revises y confirmes.
        </p>

        {!job && (
          <div className="cv-dropzone text-center p-4">
            <i className="bi bi-cloud-arrow-up display-5 text-magenta" aria-hidden="true" />
            <p className="small mb-3 mt-2">PDF, DOCX, DOC o MD · máximo 5 MB</p>
            <label htmlFor="cv-file" className="visually-hidden">
              Archivo de CV
            </label>
            <input
              id="cv-file"
              type="file"
              className="form-control"
              accept=".pdf,.docx,.doc,.md"
              onChange={pick}
            />
            <button
              type="button"
              className="btn btn-primary btn-pill mt-3"
              disabled={!file || uploading}
              onClick={upload}
            >
              {uploading ? (
                <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />
              ) : (
                <i className="bi bi-upload me-2" aria-hidden="true" />
              )}
              Subir y analizar
            </button>
          </div>
        )}

        {processing && (
          <div aria-live="polite">
            <div className="d-flex justify-content-between small fw-semibold mb-1">
              <span>
                <span
                  className="spinner-border spinner-border-sm text-primary me-2"
                  aria-hidden="true"
                />
                {job?.stage ?? 'Analizando tu CV…'}
              </span>
              <span>{progress}%</span>
            </div>
            <div
              className="progress"
              role="progressbar"
              aria-label="Avance del análisis del CV"
              aria-valuenow={progress}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <div
                className="progress-bar progress-bar-striped progress-bar-animated"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="small text-body-secondary mt-2 mb-0">
              {job?.filename} · suele tardar entre 10 y 60 segundos.
            </p>
          </div>
        )}

        {error && (
          <div className="alert alert-danger mt-3 mb-0" role="alert">
            <p className="mb-2 fw-semibold">{error}</p>
            <div className="d-flex flex-wrap gap-2">
              <button type="button" className="btn btn-sm btn-primary btn-pill" onClick={reset}>
                Intentar de nuevo
              </button>
              <button
                type="button"
                className="btn btn-sm btn-outline-primary btn-pill"
                onClick={onManual}
              >
                Cargar a mano
              </button>
            </div>
          </div>
        )}

        <div className="mt-4 pt-3 border-top">
          <button type="button" className="btn btn-link px-0" onClick={onCancel}>
            <i className="bi bi-arrow-left me-1" aria-hidden="true" />
            Volver
          </button>
        </div>
      </div>
    </div>
  );
};
