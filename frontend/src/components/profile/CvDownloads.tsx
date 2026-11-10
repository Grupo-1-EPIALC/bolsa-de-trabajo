import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { CvFormat, profileService } from '../../services/profileService';
import { ApiError, errorMessage } from '../../services/api';

interface CvDownloadsProps {
  enabled: boolean;
  layout?: 'stack' | 'row';
}

/** Estilos inyectados imperativamente en el iframe para emular una hoja de vida A4 limpia en vertical. */
const PREVIEW_CONTAINER_STYLE = `
  <style>
    html, body {
      background-color: #e9ecef !important;
      margin: 0 !important;
      padding: 0 !important;
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
      height: 100% !important;
    }
    .cv-paper-wrapper {
      box-sizing: border-box !important;
      width: 100% !important;
      max-width: 820px !important;
      margin: 2rem auto !important;
      padding: 3rem 2.5rem !important;
      background-color: #ffffff !important;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1) !important;
      border-radius: 6px !important;
      display: flex !important;
      flex-direction: column !important;
      gap: 1.25rem !important;
    }
    .cv-paper-wrapper > * {
      width: 100% !important;
    }
    hr {
      border: 0;
      border-top: 1px solid #e9ecef;
      margin: 1rem 0;
    }
  </style>
`;

/** Descarga del CV "IA friendly" en PDF o Word + vista previa estética y 100% aislada. */
export const CvDownloads: React.FC<CvDownloadsProps> = ({ enabled, layout = 'stack' }) => {
  const [busy, setBusy] = useState<CvFormat | 'preview' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [iframeLoaded, setIframeLoaded] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement | null>(null);

  // Escuchar tecla Escape para cerrar modal
  useEffect(() => {
    if (!preview) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && closePreview();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [preview]);

  // Inyección única imperativa: envuelve las secciones dentro de .cv-paper-wrapper en un solo flujo vertical
  useEffect(() => {
    if (!preview || !iframeRef.current) return;

    const doc = iframeRef.current.contentDocument || iframeRef.current.contentWindow?.document;
    if (doc) {
      doc.open();
      const wrappedHtml = `
        <!DOCTYPE html>
        <html>
          <head>
            ${PREVIEW_CONTAINER_STYLE}
          </head>
          <body>
            <div class="cv-paper-wrapper">
              ${preview}
            </div>
          </body>
        </html>
      `;
      doc.write(wrappedHtml);
      doc.close();
      setIframeLoaded(true);
    }
  }, [preview]);

  const run = async (kind: CvFormat | 'preview') => {
    setBusy(kind);
    setError(null);
    try {
      if (kind === 'preview') {
        setIframeLoaded(false);
        const html = await profileService.previewHtml();
        setPreview(html);
      } else {
        await profileService.downloadCv(kind);
      }
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

  const closePreview = () => {
    setPreview(null);
    setIframeLoaded(false);
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

      {/* Modal inyectado en document.body via Portal con renderizado vertical de hoja de papel */}
      {preview &&
        createPortal(
          <div
            className="modal fade show d-block"
            role="dialog"
            aria-modal="true"
            aria-labelledby="cv-preview-title"
            tabIndex={-1}
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              width: '100vw',
              height: '100vh',
              backgroundColor: 'rgba(0,0,0,0.65)',
              zIndex: 1060,
            }}
            onClick={closePreview}
          >
            <div
              className="modal-dialog modal-xl modal-dialog-centered"
              style={{ maxHeight: '90vh', height: '85vh', margin: '1.75rem auto' }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="modal-content h-100 border-0 shadow-lg d-flex flex-column">
                <div className="modal-header bg-light py-2 px-3">
                  <h2 id="cv-preview-title" className="modal-title h6 fw-bold mb-0">
                    <i className="bi bi-file-earmark-person me-2 text-primary" aria-hidden="true" />
                    Vista previa de tu CV
                  </h2>
                  <button
                    type="button"
                    className="btn-close"
                    aria-label="Cerrar vista previa"
                    onClick={closePreview}
                  />
                </div>
                <div className="modal-body p-0 flex-grow-1 position-relative bg-body-secondary">
                  {!iframeLoaded && (
                    <div className="position-absolute top-50 start-50 translate-middle text-center">
                      <div className="spinner-border text-primary mb-2" role="status" />
                      <div className="small text-body-secondary fw-semibold">
                        Cargando documento...
                      </div>
                    </div>
                  )}
                  <iframe
                    ref={iframeRef}
                    title="Vista previa del CV"
                    sandbox="allow-same-origin"
                    className={`w-100 h-100 border-0 ${iframeLoaded ? 'd-block' : 'd-none'}`}
                    style={{ backgroundColor: '#e9ecef' }}
                  />
                </div>
                <div className="modal-footer py-2 px-3 bg-light d-flex justify-content-between">
                  <span className="small text-body-secondary">
                    Documento optimizado para sistemas de selección (ATS).
                  </span>
                  <button
                    type="button"
                    className="btn btn-sm btn-secondary btn-pill px-4"
                    onClick={closePreview}
                  >
                    Cerrar
                  </button>
                </div>
              </div>
            </div>
          </div>,
          document.body,
        )}
    </>
  );
};
