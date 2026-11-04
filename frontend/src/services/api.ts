// Configuración centralizada de llamadas HTTP al Nginx Gateway (Puerto 8080)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080/api/v1';

export async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  // Leemos el token de sesión guardado
  const token = localStorage.getItem('access_token');

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    if (response.status === 401) {
      // Si el token expira o es inválido, limpiamos la sesión local
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || errorData.message || `Error HTTP ${response.status}`);
  }

  return response.json();
}