import { API_DOCS_PATHS, buildOpenApiConfig, redocHtml } from './api-docs';

describe('Documentación de la API (Swagger UI y ReDoc)', () => {
  it('UT-AUTH-13 publica docs, ReDoc y OpenAPI bajo el prefijo del servicio', () => {
    expect(API_DOCS_PATHS).toEqual({
      swagger: 'api/v1/auth/docs',
      redoc: 'api/v1/auth/redoc',
      openapi: 'api/v1/auth/openapi.json',
    });
    for (const path of Object.values(API_DOCS_PATHS)) {
      // El gateway sólo enruta /api/v1/auth/ a este servicio.
      expect(path.startsWith('api/v1/auth/')).toBe(true);
    }
  });

  it('el OpenAPI declara el servicio, su versión y el esquema Bearer JWT', () => {
    const config = buildOpenApiConfig('9.9.9');
    expect(config.info).toMatchObject({ title: 'auth-service', version: '9.9.9' });
    expect(config.components?.securitySchemes?.bearer).toMatchObject({
      type: 'http',
      scheme: 'bearer',
      bearerFormat: 'JWT',
    });
  });

  it('la página de ReDoc apunta al OpenAPI y escapa lo que inserta', () => {
    const html = redocHtml('/api/v1/auth/openapi.json');
    expect(html).toContain('<redoc spec-url="/api/v1/auth/openapi.json"></redoc>');
    expect(html).toMatch(/redoc@\d+\.\d+\.\d+\/bundles\/redoc\.standalone\.js/);
    expect(redocHtml('/x"><script>', '<b>')).not.toMatch(/<script>|<b>/);
  });
});
