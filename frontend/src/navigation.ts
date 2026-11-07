// Vistas de la SPA. "home" y "auth" son públicas; "app" es el área del usuario logueado.
export type View = 'home' | 'auth' | 'app';
export type AuthMode = 'login' | 'register';

/**
 * Secciones del área privada. Estudiante: panel, recomendaciones, todas las ofertas y perfil.
 * Empresa: panel, búsquedas y perfil.
 */
export type StudentSection = 'panel' | 'recommendations' | 'jobs' | 'searches' | 'profile';

/** Vista a mostrar según la sesión: sin sesión nunca se muestra el área privada. */
export function resolveView(requested: View, isAuthenticated: boolean): View {
  if (!isAuthenticated && requested === 'app') return 'home';
  if (isAuthenticated && requested !== 'app') return 'app';
  return requested;
}
