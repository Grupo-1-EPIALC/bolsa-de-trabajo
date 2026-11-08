import React, { useEffect, useState } from 'react';
import type { CompanyProfile } from '../../types/company';
import { companyService } from '../../services/companyService';
import { errorMessage } from '../../services/api';
import { CompanyLogo } from './CompanyLogo';
import { COMPANY_MODALITY, COMPANY_SIZE, labelOf } from '../../profile/labels';

interface CompanyPublicProfileModalProps {
  companyId: string;
  companyNameFallback?: string;
  onClose: () => void;
}

export const CompanyPublicProfileModal: React.FC<CompanyPublicProfileModalProps> = ({
  companyId,
  companyNameFallback,
  onClose,
}) => {
  const [company, setCompany] = useState<CompanyProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    companyService
      .getPublicProfile(companyId)
      .then((data) => {
        if (active) setCompany(data);
      })
      .catch((err) => {
        if (active) setError(errorMessage(err));
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [companyId]);

  const place = company
    ? [company.location?.city, company.location?.province, company.location?.country]
        .filter(Boolean)
        .join(', ')
    : '';

  return (
    <div
      className="modal fade show d-block"
      tabIndex={-1}
      role="dialog"
      aria-labelledby="companyPublicModalTitle"
      aria-modal="true"
      style={{ backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1055 }}
    >
      <div className="modal-dialog modal-dialog-centered modal-lg" role="document">
        <div className="modal-content border-0 shadow-lg">
          {/* Header */}
          <div className="modal-header border-bottom-0 pb-0">
            <span className="badge bg-soft text-magenta border border-primary-subtle text-uppercase">
              <i className="bi bi-building me-1" aria-hidden="true" />
              Perfil de Empresa
            </span>
            <button
              type="button"
              className="btn-close"
              aria-label="Cerrar modal"
              onClick={onClose}
            />
          </div>

          <div className="modal-body p-4">
            {loading && (
              <div className="text-center py-5">
                <span
                  className="spinner-border text-primary"
                  role="status"
                  aria-label="Cargando perfil de la empresa"
                />
              </div>
            )}

            {error && (
              <div className="alert alert-danger" role="alert">
                <i className="bi bi-exclamation-triangle-fill me-2" aria-hidden="true" />
                {error}
              </div>
            )}

            {!loading && !error && company && (
              <div className="d-grid gap-4">
                {/* Cabecera de Marca Empleadora */}
                <div className="d-flex gap-3 align-items-center bg-light p-3 rounded-3">
                  <CompanyLogo name={company.display_name || company.name || companyNameFallback || ''} url={company.logo_url} size={72} />
                  <div>
                    <h2 className="h4 fw-bold mb-1" id="companyPublicModalTitle">
                      {company.display_name || company.name || companyNameFallback}
                    </h2>
                    {company.tagline && <p className="mb-1 text-magenta fw-semibold">{company.tagline}</p>}
                    <p className="small text-body-secondary mb-0">
                      {[
                        company.industry,
                        labelOf(COMPANY_SIZE, company.size),
                        place,
                        company.founded_year ? `Fundada en ${company.founded_year}` : null,
                      ]
                        .filter(Boolean)
                        .join(' · ')}
                    </p>
                  </div>
                </div>

                {/* Descripción Institucional */}
                {company.description && (
                  <section>
                    <h3 className="h6 fw-bold mb-2">Sobre la empresa</h3>
                    <p className="small text-body-secondary style-description">{company.description}</p>
                  </section>
                )}

                {/* Modalidades de Trabajo & Beneficios */}
                <div className="row g-3">
                  {(company.work_modalities ?? []).length > 0 && (
                    <div className="col-md-6">
                      <div className="border rounded-3 p-3 bg-white h-100">
                        <h4 className="h6 fw-bold mb-2">Modalidades de Trabajo</h4>
                        <div className="d-flex flex-wrap gap-1">
                          {company.work_modalities!.map((m) => (
                            <span key={m} className="badge text-bg-light border">
                              {labelOf(COMPANY_MODALITY, m)}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {(company.benefits ?? []).length > 0 && (
                    <div className="col-md-6">
                      <div className="border rounded-3 p-3 bg-white h-100">
                        <h4 className="h6 fw-bold mb-2">Beneficios</h4>
                        <div className="d-flex flex-wrap gap-1">
                          {company.benefits!.map((b) => (
                            <span key={b} className="badge bg-soft text-magenta border border-primary-subtle">
                              <i className="bi bi-star-fill me-1" aria-hidden="true" />
                              {b}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Enlaces Web y Redes Sociales */}
                {(company.website || (company.links ?? []).length > 0) && (
                  <section>
                    <h3 className="h6 fw-bold mb-2">Sitio Web y Redes</h3>
                    <div className="d-flex flex-wrap gap-2">
                      {company.website && (
                        <a
                          href={company.website}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn btn-sm btn-outline-primary btn-pill"
                        >
                          <i className="bi bi-globe me-1" aria-hidden="true" />
                          Sitio Web
                        </a>
                      )}
                      {(company.links ?? []).map((l, idx) => (
                        <a
                          key={idx}
                          href={l.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn btn-sm btn-light border btn-pill"
                        >
                          <i className={`bi bi-${l.type === 'x' ? 'twitter-x' : l.type} me-1`} aria-hidden="true" />
                          {l.type.toUpperCase()}
                        </a>
                      ))}
                    </div>
                  </section>
                )}

                {/* Contacto Público si está habilitado */}
                {company.contact && company.contact.public && (
                  <section className="border-top pt-3">
                    <h3 className="h6 fw-bold mb-2">Contacto de Selección / RR. HH.</h3>
                    <div className="small text-body-secondary">
                      {company.contact.name && <span className="d-block"><strong>Contacto:</strong> {company.contact.name}</span>}
                      {company.contact.email && <span className="d-block"><strong>Email:</strong> {company.contact.email}</span>}
                      {company.contact.phone && <span className="d-block"><strong>Teléfono:</strong> {company.contact.phone}</span>}
                    </div>
                  </section>
                )}
              </div>
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