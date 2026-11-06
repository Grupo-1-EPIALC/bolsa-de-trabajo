// Cliente HTTP único hacia el API Gateway (same-origin /api/v1).
// - Agrega el JWT de auth-service y renueva el access token una vez ante un 401.
// - Convierte el formato común {"error": {code, message, details}} en ApiError.
import { session } from './session';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly details: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

const FALLBACK_MESSAGES: Record<number, string> = {
  401: 'Tu sesión venció. Volvé a ingresar.',
  403: 'No tenés acceso a esta sección.',
  404: 'No encontramos lo que buscabas.',
  502: 'El servicio no está respondiendo. Probá de nuevo en unos minutos.',
  503: 'El servicio no está disponible. Probá de nuevo en unos minutos.',
  504: 'El servicio tardó demasiado en responder. Probá de nuevo.',
};

async function toApiError(response: Response): Promise<ApiError> {
  const text = await response.text();
  let code = `HTTP_${response.status}`;
  let message = FALLBACK_MESSAGES[response.status] ?? `Error del servidor (${response.status})`;
  let details: Record<string, unknown> = {};
  try {
    const body = JSON.parse(text);
    if (body?.error) {
      code = body.error.code ?? code;
      message = body.error.message ?? message;
      details = body.error.details ?? {};
    } else if (typeof body?.message === 'string') {
      message = body.message;
    }
  } catch {
    // Respuesta no JSON (p. ej. página HTML de Nginx): queda el mensaje genérico.
  }
  return new ApiError(response.status, code, message, details);
}

let refreshing: Promise<boolean> | null = null;

/** Renueva el access token con el refresh token. Comparte la promesa entre pedidos simultáneos. */
function refreshAccessToken(): Promise<boolean> {
  const refreshToken = session.refreshToken();
  if (!refreshToken) return Promise.resolve(false);
  refreshing ??= fetch(`${API_BASE_URL}/auth/token/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })
    .then(async (res) => {
      if (!res.ok) return false;
      session.setTokens(await res.json());
      return true;
    })
    .catch(() => false)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

/** Hace el pedido con auth y refresh; devuelve la Response si es OK o lanza ApiError. */
export async function apiRequest(endpoint: string, options: RequestInit = {}): Promise<Response> {
  const send = () => {
    const token = session.accessToken();
    const headers = new Headers(options.headers);
    if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }
    if (token) headers.set('Authorization', `Bearer ${token}`);
    return fetch(`${API_BASE_URL}${endpoint}`, { ...options, headers });
  };

  let response: Response;
  try {
    response = await send();
    if (response.status === 401 && session.refreshToken()) {
      if (await refreshAccessToken()) {
        response = await send();
      }
    }
  } catch {
    throw new ApiError(0, 'NETWORK_ERROR', 'No se pudo conectar con el servidor.');
  }

  if (!response.ok) {
    if (response.status === 401) session.clear();
    throw await toApiError(response);
  }
  return response;
}

/** Pedido JSON. Devuelve undefined en respuestas sin cuerpo (204). */
export async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const response = await apiRequest(endpoint, options);
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  if (!text) return undefined as T;
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new ApiError(response.status, 'INVALID_RESPONSE', 'Respuesta del servidor no válida.');
  }
}

/** Mensaje legible para mostrar al usuario a partir de cualquier error. */
export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error) return err.message;
  return 'Ocurrió un error inesperado.';
}

/** Lista "campo: mensaje" a partir de un 422 INVALID_INPUT (details.errors o details.fields). */
export function validationMessages(err: unknown): string[] {
  if (!(err instanceof ApiError)) return [];
  const errors = err.details.errors;
  if (Array.isArray(errors)) {
    return errors.map((e: { loc?: unknown[]; msg?: string }) => {
      const loc = (e.loc ?? []).filter((p) => p !== 'body').join('.');
      return loc ? `${loc}: ${e.msg ?? ''}` : (e.msg ?? '');
    });
  }
  const fields = err.details.fields;
  if (Array.isArray(fields)) return fields.map((f) => `${String(f)}: completar`);
  return [];
}
