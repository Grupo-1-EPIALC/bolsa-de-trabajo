// src/App.tsx
import React, { useState, useEffect } from 'react';
import { RuleScoreCard } from './components/RuleScoreCard';
import { AISuggestionCard } from './components/AISuggestionCard';
import { StudentProfile } from './components/StudentProfile';
import { AuthForm } from './components/AuthForm';
import { matchingService } from './services/matchingService';
import { MOCK_STUDENT_PROFILE } from './services/mockData';
import { MatchResponse } from './types/matching';
import { UserCheck, User, LogIn, LogOut, Briefcase, Menu, X, CheckCircle } from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'profile' | 'matching' | 'auth'>('matching');
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);

  // Estado de sesión en Frontend
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);

  // 🍞 Estado del Toast de Bienvenida No Invasivo
  const [showWelcomeToast, setShowWelcomeToast] = useState<boolean>(false);

  // Estado para la evaluación de compatibilidad
  const [matchData, setMatchData] = useState<MatchResponse | null>(null);
  const [loadingMatch, setLoadingMatch] = useState<boolean>(true);
  const [matchError, setMatchError] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      setIsAuthenticated(true);
    }

    setLoadingMatch(true);
    matchingService
      .getMatchScore('stu-001', 'job-001')
      .then((data) => {
        if (data && Object.keys(data).length > 0) {
          setMatchData(data);
        }
        setLoadingMatch(false);
      })
      .catch((err: any) => {
        console.error('Error al obtener scoring/matching:', err);
        setMatchError(err.message || 'Error al conectar con la API de Matching');
        setLoadingMatch(false);
      });
  }, []);

  // 🚀 Al autenticarse con éxito: dispara el Toast de 3 seg y redirige a la pantalla principal
  const handleLoginSuccess = () => {
    setIsAuthenticated(true);
    setActiveTab('matching');
    setShowWelcomeToast(true);

    // Desaparece automáticamente a los 3 segundos (3000 ms)
    setTimeout(() => {
      setShowWelcomeToast(false);
    }, 3000);
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setIsAuthenticated(false);
    setShowWelcomeToast(false);
    setActiveTab('auth');
  };

  const handleTabSelect = (tab: 'profile' | 'matching' | 'auth') => {
    setActiveTab(tab);
    setMobileMenuOpen(false);
  };

  return (
    <div className="min-h-screen bg-slate-100 text-slate-800 font-sans antialiased flex flex-col w-full overflow-x-hidden relative">
      {/* 🍞 Toast de Bienvenida No Invasivo (Flotante arriba a la derecha, desaparece en 3 seg) */}
      {showWelcomeToast && (
        <div className="fixed top-24 left-1/2 -translate-x-1/2 z-50 flex items-center space-x-2.5 bg-emerald-900 text-white px-5 py-2.5 rounded-2xl shadow-xl border border-emerald-700 pointer-events-none">
          <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
          <span className="text-xs sm:text-sm font-semibold tracking-wide">¡Ingreso exitoso!</span>
        </div>
      )}

      {/* Header Fijo */}
      <header className="bg-slate-900 text-white shadow-lg border-b border-slate-800 sticky top-0 z-50 relative">
        <div className="w-full px-4 sm:px-8 h-20 flex items-center justify-between">
          <div className="flex items-center space-x-3.5">
            <div className="h-10 w-10 sm:h-11 sm:w-11 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md shrink-0">
              <Briefcase className="w-5 h-5 sm:w-6 sm:h-6" />
            </div>
            <div>
              <span className="font-extrabold text-white text-lg sm:text-xl tracking-tight block leading-tight">
                Bolsa de Trabajo
              </span>
              <span className="text-[11px] sm:text-xs text-slate-400 font-medium">
                Matching Auditado & IA{' '}
              </span>
            </div>
          </div>

          {/* Navegación Desktop */}
          <nav className="hidden md:flex items-center space-x-2">
            <button
              onClick={() => handleTabSelect('matching')}
              className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl text-sm font-bold transition-all ${
                activeTab === 'matching'
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800'
              }`}
            >
              <UserCheck className="w-4.5 h-4.5" />
              <span>Matching & IA</span>
            </button>

            <button
              onClick={() => handleTabSelect('profile')}
              className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl text-sm font-bold transition-all ${
                activeTab === 'profile'
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800'
              }`}
            >
              <User className="w-4.5 h-4.5" />
              <span>Mi Perfil (CV)</span>
            </button>

            {isAuthenticated ? (
              <button
                onClick={handleLogout}
                className="flex items-center space-x-2 px-4 py-2.5 rounded-xl text-sm font-bold bg-red-500/10 text-red-400 hover:bg-red-600 hover:text-white transition-all border border-red-500/20"
              >
                <LogOut className="w-4.5 h-4.5" />
                <span>Cerrar Sesión</span>
              </button>
            ) : (
              <button
                onClick={() => handleTabSelect('auth')}
                className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl text-sm font-bold transition-all ${
                  activeTab === 'auth'
                    ? 'bg-blue-600 text-white shadow-md shadow-blue-600/30'
                    : 'text-slate-300 hover:text-white hover:bg-slate-800'
                }`}
              >
                <LogIn className="w-4.5 h-4.5" />
                <span>Ingresar</span>
              </button>
            )}
          </nav>

          {/* Botón Menú Mobile */}
          <div className="flex md:hidden">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2.5 rounded-xl bg-slate-800 text-slate-200 hover:text-white hover:bg-slate-700 transition-all border border-slate-700"
              aria-label="Abrir menú"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* Dropdown Mobile */}
        {mobileMenuOpen && (
          <div className="md:hidden absolute top-full right-4 sm:right-8 w-auto min-w-[210px] max-w-[260px] bg-slate-900 border-x border-b border-slate-700 rounded-b-2xl p-2.5 shadow-2xl space-y-1 z-50">
            <button
              onClick={() => handleTabSelect('matching')}
              className={`w-full flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all ${
                activeTab === 'matching'
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-200 hover:bg-slate-800'
              }`}
            >
              <UserCheck className="w-4 h-4 text-blue-400" />
              <span>Matching & IA</span>
            </button>

            <button
              onClick={() => handleTabSelect('profile')}
              className={`w-full flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all ${
                activeTab === 'profile'
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-200 hover:bg-slate-800'
              }`}
            >
              <User className="w-4 h-4 text-blue-400" />
              <span>Mi Perfil (CV)</span>
            </button>

            {isAuthenticated ? (
              <button
                onClick={() => {
                  handleLogout();
                  setMobileMenuOpen(false);
                }}
                className="w-full flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-xs font-bold text-red-400 hover:bg-red-950/40 transition-all"
              >
                <LogOut className="w-4 h-4 text-red-400" />
                <span>Cerrar Sesión</span>
              </button>
            ) : (
              <button
                onClick={() => handleTabSelect('auth')}
                className={`w-full flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all ${
                  activeTab === 'auth'
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-200 hover:bg-slate-800'
                }`}
              >
                <LogIn className="w-4 h-4 text-blue-400" />
                <span>Ingresar</span>
              </button>
            )}
          </div>
        )}
      </header>

      {/* Contenido Principal */}
      <main className="w-full px-4 sm:px-8 py-6 sm:py-8 flex-1">
        {activeTab === 'matching' && (
          <div className="w-full space-y-6 sm:space-y-8">
            <div className="bg-white p-5 sm:p-7 rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <h1 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">
                  Evaluación de Compatibilidad
                </h1>
                <p className="text-xs sm:text-sm text-slate-600 mt-1">
                  Candidato: <span className="font-bold text-slate-800">Lucía Pérez (stu-001)</span>{' '}
                  — Puesto:{' '}
                  <span className="font-bold text-slate-800">
                    Desarrollador Frontend Trainee (job-001)
                  </span>
                </p>
              </div>
              <span className="self-start md:self-auto text-xs sm:text-sm font-bold px-3.5 py-1.5 bg-emerald-100 text-emerald-900 border border-emerald-300 rounded-full">
                Búsqueda Activa
              </span>
            </div>

            {matchError && (
              <div className="p-4 bg-red-50 text-red-700 rounded-xl border border-red-200 text-sm font-bold">
                {matchError} (Mostrando datos locales de respaldo)
              </div>
            )}

            {loadingMatch ? (
              <div className="p-8 text-center text-slate-500 font-bold">
                Cargando puntuación de matching...
              </div>
            ) : (
              <div className="w-full grid grid-cols-1 xl:grid-cols-2 gap-6 sm:gap-8 items-start">
                <RuleScoreCard scoreData={matchData?.rule_based} />
                <AISuggestionCard aiData={matchData?.ai_recommendations} />
              </div>
            )}
          </div>
        )}

        {activeTab === 'profile' && (
          <div className="w-full">
            <StudentProfile initialProfile={MOCK_STUDENT_PROFILE} />
          </div>
        )}

        {activeTab === 'auth' && (
          <div className="w-full min-h-[65vh] flex items-center justify-center py-6">
            <div className="w-full max-w-md">
              <AuthForm onLoginSuccess={handleLoginSuccess} />
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
