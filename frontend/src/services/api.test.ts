import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, apiFetch } from './api';

// Entorno node: localStorage mínimo para la sesión (sin tokens = pedido anónimo, como el login).
function memoryStorage(): Storage {
  const data = new Map<string, string>();
  return {
    get length() {
      return data.size;
    },
    clear: () => data.clear(),
    getItem: (k) => data.get(k) ?? null,
    key: (i) => [...data.keys()][i] ?? null,
    removeItem: (k) => void data.delete(k),
    setItem: (k, v) => void data.set(k, String(v)),
  };
}

function respond(status: number, body: string, contentType: string) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => new Response(body, { status, headers: { 'Content-Type': contentType } })),
  );
}

async function failure(): Promise<ApiError> {
  try {
    await apiFetch('/auth/login', { method: 'POST', body: '{}' });
  } catch (err) {
    return err as ApiError;
  }
  throw new Error('el pedido debía fallar');
}

describe('apiFetch · rate limit (429)', () => {
  beforeEach(() => vi.stubGlobal('localStorage', memoryStorage()));
  afterEach(() => vi.unstubAllGlobals());

  it('usa el mensaje del gateway cuando viene en el formato común', async () => {
    respond(
      429,
      JSON.stringify({
        error: {
          code: 'TOO_MANY_REQUESTS',
          message: 'Demasiados intentos. Esperá un minuto y volvé a probar.',
        },
      }),
      'application/json',
    );
    const err = await failure();
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(429);
    expect(err.code).toBe('TOO_MANY_REQUESTS');
    expect(err.message).toMatch(/Esperá un minuto/);
  });

  it('explica que hay que esperar aunque la respuesta no sea JSON', async () => {
    respond(429, '<html><title>429 Too Many Requests</title></html>', 'text/html');
    const err = await failure();
    expect(err.status).toBe(429);
    expect(err.message).toBe('Demasiados intentos. Esperá un minuto y volvé a probar.');
    expect(err.message).not.toMatch(/Error del servidor/);
  });
});
