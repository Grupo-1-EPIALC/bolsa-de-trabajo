import React from 'react';
import { API_DOCS } from '../../admin/apiDocs';

const NewTab: React.FC<{
  href: string;
  icon: string;
  children: React.ReactNode;
  label: string;
}> = ({ href, icon, children, label }) => (
  <a
    className="btn btn-sm btn-outline-primary btn-pill"
    href={href}
    target="_blank"
    rel="noopener noreferrer"
    aria-label={`${label} (se abre en otra pestaña)`}
  >
    <i className={`bi ${icon} me-1`} aria-hidden="true" />
    {children}
  </a>
);

/** Links a Swagger UI, ReDoc y el OpenAPI de cada servicio REST. */
export const ApiDocsLinks: React.FC = () => (
  <section aria-labelledby="admin-api-docs">
    <h2 id="admin-api-docs" className="section-title h4">
      Documentación de las APIs
    </h2>
    <div className="row g-3">
      {API_DOCS.map((api) => (
        <div className="col-12 col-md-6" key={api.service}>
          <div className="card card-elevated h-100">
            <div className="card-body d-flex flex-column gap-2">
              <div>
                <h3 className="h6 fw-bold mb-1">
                  <code>{api.service}</code>
                </h3>
                <p className="small text-body-secondary mb-0">{api.description}</p>
              </div>
              <div className="d-flex flex-wrap gap-2 mt-auto">
                <NewTab href={api.swagger} icon="bi-braces" label={`Swagger UI de ${api.service}`}>
                  Swagger UI
                </NewTab>
                <NewTab href={api.redoc} icon="bi-book" label={`ReDoc de ${api.service}`}>
                  ReDoc
                </NewTab>
                <NewTab
                  href={api.openapi}
                  icon="bi-filetype-json"
                  label={`OpenAPI JSON de ${api.service}`}
                >
                  OpenAPI
                </NewTab>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
    <p className="small text-body-secondary mt-2 mb-0">
      En Swagger UI, &quot;Authorize&quot; acepta el access token de una sesión para probar los
      endpoints protegidos.
    </p>
  </section>
);
