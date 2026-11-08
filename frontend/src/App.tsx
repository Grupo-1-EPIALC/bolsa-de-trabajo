import React, { useEffect, useState } from 'react';
import { SiteHeader } from './components/layout/SiteHeader';
import { SiteFooter } from './components/layout/SiteFooter';
import { LandingPage } from './pages/LandingPage';
import { AuthPage } from './pages/AuthPage';
import { StudentArea } from './pages/StudentArea';
import { CompanyArea } from './pages/CompanyArea';
import { ConfirmEmailPage } from './pages/ConfirmEmailPage';
import { ResetPasswordConfirmPage } from './pages/ResetPasswordConfirmPage';
import { AdminArea } from './pages/AdminArea';
import { authService } from './services/authService';
import { session, SessionUser } from './services/session';
import { AuthMode, StudentSection, View, resolveView } from './navigation';

/**
 * Sin sesión → portada (y acceso/registro).
 * Estudiante → su área: alta de perfil si no tiene, o panel con recomendaciones, perfil y CV.
 * Empresa → su panel y búsquedas. Admin → cuentas y configuración de matching.
 */
export const App: React.FC = () => {
  const [user, setUser] = useState<SessionUser | null>(() => session.user());
  const [requestedView, setRequestedView] = useState<View>('home');
  const [authMode, setAuthMode] = useState<AuthMode>('login');
  const [section, setSection] = useState<StudentSection>('panel');
  const [toast, setToast] = useState<string | null>(null);
  const activeView = resolveView(requestedView, !!user);

  // Detección de parámetros y rutas en la URL de entrada (auth_frontend.md §1 y §5)
  const pathname = window.location.pathname;
  const searchParams = new URLSearchParams(window.location.search);

  // Tokens de mail
  const emailConfirmToken = searchParams.get('token');
  const isConfirmingEmail = pathname.includes('/auth/email/confirm') && Boolean(emailConfirmToken);

  // Tokens de reset de contraseña
  const resetPasswordToken = searchParams.get('token');
  const isResettingPassword =
    pathname.includes('/auth/password/reset/confirm') && Boolean(resetPasswordToken);

  // SI HAY UN TOKEN DE RECUPERACIÓN EN LA URL, LIMPIAMOS CUALQUIER SESIÓN PREVIA
  useEffect(() => {
    if (isResettingPassword || isConfirmingEmail) {
      session.clear(); // Limpia localStorage y reinicia el estado 'user' a null
    }
  }, [isResettingPassword, isConfirmingEmail]);

  // Si la sesión termina (logout o refresh vencido) se vuelve a la portada.
  useEffect(
    () =>
      session.subscribe((u) => {
        setUser(u);
        if (!u) setRequestedView('home');
      }),
    [],
  );

  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [activeView, section]);

  const openAuth = (mode: AuthMode) => {
    setAuthMode(mode);
    setRequestedView('auth');
  };

  const handleAuthSuccess = (u: SessionUser, mode: AuthMode) => {
    setUser(u);
    setSection('panel');
    setRequestedView('app');
    setToast(mode === 'register' ? '¡Cuenta creada!' : '¡Ingreso exitoso!');
    setTimeout(() => setToast(null), 3000);
  };

  const goToSection = (s: StudentSection) => {
    setSection(s);
    setRequestedView('app');
  };

  return (
    <div className="d-flex flex-column min-vh-100">
      {toast && (
        <div className="toast-floating" role="status" aria-live="polite">
          <div className="d-flex align-items-center gap-2 text-bg-success rounded-pill shadow px-4 py-2 fw-semibold small">
            <i className="bi bi-check-circle-fill" aria-hidden="true" />
            {toast}
          </div>
        </div>
      )}

      <SiteHeader
        user={user}
        activeView={activeView}
        section={section}
        onNavigate={setRequestedView}
        onSection={goToSection}
        onAuth={openAuth}
        onLogout={() => authService.logout()}
      />

      <main className="flex-grow-1">
        {/* INTERCEPTOR 1: Confirmación de Email */}
        {isConfirmingEmail && emailConfirmToken ? (
          <ConfirmEmailPage
            token={emailConfirmToken}
            onGoToLogin={() => {
              window.history.replaceState({}, document.title, '/');
              openAuth('login');
            }}
          />
        ) : isResettingPassword && resetPasswordToken ? (
          /* INTERCEPTOR 2: Restablecimiento de Contraseña */
          <ResetPasswordConfirmPage
            token={resetPasswordToken}
            onSuccess={() => {
              window.history.replaceState({}, document.title, '/');
              setToast('¡Contraseña actualizada con éxito! Ingresá con tu nueva clave.');
              openAuth('login');
              setTimeout(() => setToast(null), 4000);
            }}
          />
        ) : (
          /* NAVEGACIÓN NORMAL SPA (CON ROLES UNIFICADOS) */
          <>
            {activeView === 'home' && <LandingPage onAuth={openAuth} />}
            {activeView === 'auth' && <AuthPage mode={authMode} onSuccess={handleAuthSuccess} />}
            {activeView === 'app' && user?.role === 'student' && (
              <StudentArea key={user.id} section={section} onSection={goToSection} />
            )}
            {activeView === 'app' && user?.role === 'company' && (
              <CompanyArea key={user.id} user={user} section={section} onSection={goToSection} />
            )}
            {activeView === 'app' && user?.role === 'admin' && (
              <AdminArea key={user.id} user={user} section={section} onSection={goToSection} />
            )}
          </>
        )}
      </main>

      <SiteFooter
        user={user}
        onNavigate={setRequestedView}
        onSection={goToSection}
        onAuth={openAuth}
      />
    </div>
  );
};

export default App;