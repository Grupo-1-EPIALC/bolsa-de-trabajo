// Sesión del usuario en el navegador: tokens de auth-service y datos públicos del usuario.

export type Role = 'student' | 'company' | 'admin';

export interface SessionUser {
  id: string;
  email: string;
  role: Role;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
}

const ACCESS = 'access_token';
const REFRESH = 'refresh_token';
const USER = 'session_user';

type Listener = (user: SessionUser | null) => void;
const listeners = new Set<Listener>();

function notify(user: SessionUser | null) {
  listeners.forEach((fn) => fn(user));
}

export const session = {
  accessToken: (): string | null => localStorage.getItem(ACCESS),
  refreshToken: (): string | null => localStorage.getItem(REFRESH),

  user(): SessionUser | null {
    const raw = localStorage.getItem(USER);
    if (!raw || !localStorage.getItem(ACCESS)) return null;
    try {
      return JSON.parse(raw) as SessionUser;
    } catch {
      return null;
    }
  },

  setTokens(tokens: TokenPair) {
    localStorage.setItem(ACCESS, tokens.access_token);
    localStorage.setItem(REFRESH, tokens.refresh_token);
  },

  start(user: SessionUser, tokens: TokenPair) {
    this.setTokens(tokens);
    localStorage.setItem(USER, JSON.stringify(user));
    notify(user);
  },

  clear() {
    const hadSession = !!localStorage.getItem(ACCESS);
    localStorage.removeItem(ACCESS);
    localStorage.removeItem(REFRESH);
    localStorage.removeItem(USER);
    if (hadSession) notify(null);
  },

  /** Avisa cuando la sesión empieza o termina (p. ej. refresh vencido). */
  subscribe(fn: Listener): () => void {
    listeners.add(fn);
    return () => listeners.delete(fn);
  },
};
