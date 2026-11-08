import { INestApplication } from '@nestjs/common';
import { DocumentBuilder, OpenAPIObject, SwaggerModule } from '@nestjs/swagger';
import type { Request, Response } from 'express';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Documentación de la API bajo el prefijo del servicio, así pasa por el gateway sin rutas nuevas:
 *   /api/v1/auth/docs          Swagger UI
 *   /api/v1/auth/redoc         ReDoc
 *   /api/v1/auth/openapi.json  OpenAPI 3 (lo generan los controllers y DTOs)
 */
export const API_DOCS_PATHS = {
  swagger: 'api/v1/auth/docs',
  redoc: 'api/v1/auth/redoc',
  openapi: 'api/v1/auth/openapi.json',
} as const;

const REDOC_SCRIPT = 'https://cdn.jsdelivr.net/npm/redoc@2.1.5/bundles/redoc.standalone.js';

function serviceVersion(): string {
  try {
    const pkg = JSON.parse(readFileSync(resolve(__dirname, '..', '..', 'package.json'), 'utf8'));
    return typeof pkg.version === 'string' ? pkg.version : '0.0.0';
  } catch {
    return '0.0.0';
  }
}

export function buildOpenApiConfig(version = serviceVersion()): Omit<OpenAPIObject, 'paths'> {
  return new DocumentBuilder()
    .setTitle('auth-service')
    .setDescription(
      'Autenticación, usuarios y empresas de la Bolsa de Trabajo (JWT RS256). ' +
        'Contrato: contracts/auth.md. Los endpoints con candado piden ' +
        '`Authorization: Bearer <access_token>`; los de `admin` además el rol admin.',
    )
    .setVersion(version)
    .addBearerAuth({ type: 'http', scheme: 'bearer', bearerFormat: 'JWT' })
    .build();
}

/** Página de ReDoc (estática; el JS se carga del CDN, como hace Swagger UI). */
export function redocHtml(openapiUrl: string, title = 'auth-service · ReDoc'): string {
  const safe = (value: string) => value.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
  return `<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>${safe(title)}</title>
    <style>body { margin: 0; }</style>
  </head>
  <body>
    <redoc spec-url="${safe(openapiUrl)}"></redoc>
    <script src="${REDOC_SCRIPT}"></script>
  </body>
</html>`;
}

export function setupApiDocs(app: INestApplication): void {
  const document = SwaggerModule.createDocument(app, buildOpenApiConfig());
  SwaggerModule.setup(API_DOCS_PATHS.swagger, app, document, {
    jsonDocumentUrl: API_DOCS_PATHS.openapi,
    customSiteTitle: 'auth-service · Swagger UI',
    swaggerOptions: { persistAuthorization: true },
  });
  const html = redocHtml(`/${API_DOCS_PATHS.openapi}`);
  app.getHttpAdapter().get(`/${API_DOCS_PATHS.redoc}`, (_req: Request, res: Response) => {
    res.type('html').send(html);
  });
}
