import React, { useState } from 'react';
import { RuleScoreCard } from './components/RuleScoreCard';
import { AISuggestionCard } from './components/AISuggestionCard';
import { StudentProfile } from './components/StudentProfile';
import { AuthForm } from './components/AuthForm';
import { MOCK_STUDENT_PROFILE } from './services/mockData';
import { MatchResponse } from './types/matching';
import { UserCheck, User, LogIn, Briefcase, Menu, X } from 'lucide-react';

const MOCK_MATCH: MatchResponse = {
  profile_id: 'prof-01',
  job_id: 'job-01',
  rule_based: {
    origin: 'RULES',
    engine_version: '0.1.0',
    score: 82.5,
    excluding_cap_applied: false,
    breakdown: {
      required_skills: 45,
      desired_skills: 15,
      skill_levels: 12.5,
      experience: 5,
      education: 5,
      languages: 0,
    },
    missing_skills: [
      { skill: 'TypeScript', required_level: 2, current_level: 0, gap: 2, priority: 'alta', kind: 'required' },
      { skill: 'Docker', required_level: 2, current_level: 0, gap: 2, priority: 'media', kind: 'desired' },
    ],
  },
  ai_recommendations: {
    origin: 'AI',
    model: 'nvidia/llama-3.1-70b-instruct',
    generated_at: '2026-11-04T10:00:00Z',
    prompt_version: '1.0.0',
    disclaimer: 'Sugerencia generada por IA orientativa. Los puntajes oficiales se basan strictly en las reglas del sistema.',
    items: [
      { type: 'course', skill: 'TypeScript', text: 'Realizar un taller práctico de TypeScript enfocado en React SPA para elevar nivel 0 a 2.', priority: 'alta' },
      { type: 'profile_improvement', text: 'Subir al perfil proyectos personales que utilicen Docker compose local.', priority: 'media' },
    ],
  },
};

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'profile' | 'matching' | 'auth'>('matching');
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);

  const handleTabSelect = (tab: 'profile' | 'matching' | 'auth') => {
    setActiveTab(tab);
    setMobileMenuOpen(false); // Cierra automáticamente al hacer clic en una pestaña
  };

  return (
    <div className="min-h-screen bg-slate-100 text-slate-800 font-sans antialiased flex flex-col w-full overflow-x-hidden">
      {/* Header con posicionamiento relativo para anclar el desplegable */}
      <header className="bg-slate-900 text-white shadow-lg border-b border-slate-800 sticky top-0 z-50 relative">
        <div className="w-full px-4 sm:px-8 h-20 flex items-center justify-between">
          
          {/* Logo / Nombre de la App */}
          <div className="flex items-center space-x-3.5">
            <div className="h-10 w-10 sm:h-11 sm:w-11 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md shrink-0">
              <Briefcase className="w-5 h-5 sm:w-6 sm:h-6" />
            </div>
            <div>
              <span className="font-extrabold text-white text-lg sm:text-xl tracking-tight block leading-tight">
                Bolsa de Trabajo UTN
              </span>
              <span className="text-[11px] sm:text-xs text-slate-400 font-medium">Matching Auditado & IA (TP2)</span>
            </div>
          </div>

          {/* Navegación Desktop (Visible sólo de md: en adelante) */}
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
          </nav>

          {/* Botón Hamburguesa en Mobile */}
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

        {/* 🚀 MENÚ FLOTANTE PEGADO AL HEADER Y AUTOMÁTICAMENTE OCULTO EN DESKTOP (md:hidden) */}
        {mobileMenuOpen && (
          <div className="md:hidden absolute top-full right-0 w-auto min-w-[210px] max-w-[260px] bg-slate-900 border-x border-b border-slate-800 rounded-bl-2xl p-2.5 shadow-2xl space-y-1 z-50">
            <button
              onClick={() => handleTabSelect('matching')}
              className={`w-full flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all ${
                activeTab === 'matching'
                  ? 'bg-blue-600 text-white shadow-xs'
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
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'text-slate-200 hover:bg-slate-800'
              }`}
            >
              <User className="w-4 h-4 text-blue-400" />
              <span>Mi Perfil (CV)</span>
            </button>

            <button
              onClick={() => handleTabSelect('auth')}
              className={`w-full flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-xs font-bold transition-all ${
                activeTab === 'auth'
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'text-slate-200 hover:bg-slate-800'
              }`}
            >
              <LogIn className="w-4 h-4 text-blue-400" />
              <span>Ingresar</span>
            </button>
          </div>
        )}
      </header>

      {/* Contenido Principal Adaptativo Full Width */}
      <main className="w-full px-4 sm:px-8 py-6 sm:py-8 flex-1">
        {activeTab === 'matching' && (
          <div className="w-full space-y-6 sm:space-y-8">
            <div className="bg-white p-5 sm:p-7 rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <h1 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">
                  Evaluación de Compatibilidad
                </h1>
                <p className="text-xs sm:text-sm text-slate-600 mt-1">
                  Candidato: <span className="font-bold text-slate-800">Lucía Pérez</span> — Puesto: <span className="font-bold text-slate-800">Desarrollador Frontend Trainee</span>
                </p>
              </div>
              <span className="self-start md:self-auto text-xs sm:text-sm font-bold px-3.5 py-1.5 bg-emerald-100 text-emerald-900 border border-emerald-300 rounded-full">
                Búsqueda Activa
              </span>
            </div>

            <div className="w-full grid grid-cols-1 xl:grid-cols-2 gap-6 sm:gap-8 items-start">
              <RuleScoreCard scoreData={MOCK_MATCH.rule_based} />
              <AISuggestionCard aiData={MOCK_MATCH.ai_recommendations} />
            </div>
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
              <AuthForm />
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default App;