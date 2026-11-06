import React, { useEffect, useState } from 'react';
import { CvFormat, profileService } from '../../services/profileService';
import { ApiError, errorMessage } from '../../services/api';

interface CvDownloadsProps {
  enabled: boolean;
  layout?: 'stack' | 'row';
}

/** Descarga del CV "IA friendly" en PDF o Word + vista previa (contrato §8). */
export const CvDownloads: React.FC<CvDownloadsProps> = ({ enabled, layout = 'stack' }) => {
  const [busy, setBusy] = useState<CvFormat | 'preview' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);

  useEffect(() => {
    if (!preview) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setPreview(null);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [preview]);

  const run = async (kind: CvFormat | 'preview') => {
    setBusy(kind);
    setError(null);
    try {
      if (kind === 'preview') setPreview(await profileService.previewHtml());
      else await profileService.downloadCv(kind);
    } catch (err) {
      const missing =
        err instanceof ApiError && Array.isArray(err.details.missing)
          ? ` Falta: ${(err.details.missing as Array<{ message?: string } | string>)
              .map((m) => (typeof m === 'string' ? m : m.message))
              .join(', ')}.`
          : '';
      setError(errorMessage(err) + missing);
    } finally {
      setBusy(null);
    }
  };

  const spinner = (kind: CvFormat | 'preview') =>
    busy === kind ? (
      <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />
    ) : null;

  return (
    <>
      <div className={layout === 'row' ? 'd-flex flex-wrap gap-2' : 'd-grid gap-2'}>
        <button
          type="button"
          className="btn btn-primary btn-pill"
          disabled={!enabled || !!busy}
          onClick={() => run('pdf')}
        >
          {spinner('pdf') ?? <i className="bi bi-file-earmark-pdf me-2" aria-hidden="true" />}
          Descargar PDF
        </button>
        <button
          type="button"
          className="btn btn-outline-primary btn-pill"
          disabled={!enabled || !!busy}
          onClick={() => run('docx')}
        >
          {spinner('docx') ?? <i className="bi bi-file-earmark-word me-2" aria-hidden="true" />}
          Descargar Word
        </button>
        <button
          type="button"
          className="btn btn-link"
          disabled={!enabled || !!busy}
          onClick={() => run('preview')}
        >
          {spinner('preview') ?? <i className="bi bi-eye me-2" aria-hidden="true" />}
          Vista previa
        </button>
      </div>
      {!enabled && (
        <p className="small text-body-secondary mt-2 mb-0">
          Se habilita cuando completás el paso "Datos del CV".
        </p>
      )}
      {error && (
        <div className="alert alert-danger small mt-2 mb-0" role="alert">
          {error}
        </div>
      )}

      {preview && (
        <>
          <div
            className="modal d-block"
            role="dialog"
            aria-modal="true"
            aria-labelledby="cv-preview-title"
            onClick={() => setPreview(null)}
          >
            <div
              className="modal-dialog modal-xl modal-dialog-scrollable"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="modal-content">
                <div className="modal-header">
                  <h2 id="cv-preview-title" className="modal-title h5">
                    Vista previa de tu CV
                  </h2>
                  <button
                    type="button"
                    className="btn-close"
                    aria-label="Cerrar"
                    onClick={() => setPreview(null)}
                  />
                </div>
                <div className="modal-body p-0">
                  <iframe
                    title="Vista previa del CV"
                    sandbox=""
                    srcDoc={preview}
                    className="w-100 border-0"
                    style={{ height: '75vh' }}
                  />
                </div>
              </div>
            </div>
          </div>
          <div className="modal-backdrop show" />
        </>
      )}
    </>
  );
};
