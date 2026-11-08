// Documentación de las APIs REST (Swagger UI y ReDoc), servida por cada servicio bajo su
// prefijo detrás del gateway. mcp-tools y n8n no tienen API REST pública.

export interface ApiDocsEntry {
  service: string;
  description: string;
  swagger: string;
  redoc: string;
  openapi: string;
}

const entry = (service: string, resource: string, description: string): ApiDocsEntry => ({
  service,
  description,
  swagger: `/api/v1/${resource}/docs`,
  redoc: `/api/v1/${resource}/redoc`,
  openapi: `/api/v1/${resource}/openapi.json`,
});

export const API_DOCS: readonly ApiDocsEntry[] = [
  entry('auth-service', 'auth', 'Cuentas, login, tokens JWT y administración de usuarios.'),
  entry('profile-service', 'profiles', 'Perfiles de estudiantes y empresas, CV y logo.'),
  entry('jobs-service', 'jobs', 'Ofertas y búsquedas de las empresas.'),
  entry('matching-service', 'matches', 'Compatibilidad por reglas, rankings y recomendaciones.'),
];
