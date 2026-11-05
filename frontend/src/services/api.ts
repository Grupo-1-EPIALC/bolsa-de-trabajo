// Configuración centralizada de llamadas HTTP al Nginx Gateway (Puerto 8080)
// src/services/api.ts
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080/api/v1';

export async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('access_token');

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    // 1. Manejo de status 304 Not Modified (sin cuerpo)
    if (response.status === 304) {
      return {} as T;
    }

    // 2. Si el servidor respondió un error HTTP (404, 500, 502, 504, etc.)
    if (!response.ok) {
      if (response.status === 401) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
      }

      // Intentamos leer el cuerpo de la respuesta de forma segura
      const text = await response.text();
      let errorMessage = `El servidor respondió con un error (Código ${response.status})`;

      try {
        const errorData = JSON.parse(text);
        errorMessage = errorData.detail || errorData.message || errorMessage;
      } catch {
        // Si no se puede parsear como JSON (por ejemplo, devolvió HTML <!DOCTYPE html> de Nginx)
        if (response.status === 502 || response.status === 504) {
          errorMessage = 'El servidor o microservicio no está respondiendo en este momento.';
        } else if (response.status === 404) {
          errorMessage = 'El recurso o servicio solicitado no se encuentra disponible.';
        }
      }

      throw new Error(errorMessage);
    }

    // 3. Si la respuesta fue 200 OK pero el servidor devuelve HTML u otro texto no-JSON
    const text = await response.text();
    try {
      return JSON.parse(text) as T;
    } catch {
      throw new Error('Formato de respuesta del servidor no válido.');
    }
  } catch (err: any) {
    // 4. Si ocurrió un fallo de red total (servidor caído o sin conexión)
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      throw new Error('No se pudo establecer conexión con el servidor (API Gateway).');
    }
    throw err;
  }
}