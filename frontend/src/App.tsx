import { useState } from 'react';
import { RuleScoreCard } from './components/RuleScoreCard';
import { AISuggestionCard } from './components/AISuggestionCard';
import { StudentProfile } from './components/StudentProfile';
import { AuthForm } from './components/AuthForm';
import { MatchResponse } from './types/matching';

export const APP_TITLE = 'Bolsa de Trabajo';

export function App() {
  const [activeTab, setActiveTab] = useState<'auth' | 'profile' | 'matching'>('matching');

  // Estado completo con los datos de prueba
  const [matchData] = useState<MatchResponse>({
    rule_based: {
      origin: 'RULES',
      engine_version: 'scoring-1.0.0',
      score: 72.5,
      breakdown: {
        required_skills: 40,
        desired_skills: 7.5,
        levels: 12,
        experience: 8,
        education: 5,
        languages: 0,
      },
      missing_skills: [
        { skill: 'docker', required_level: 3, current_level: 0 },
        { skill: 'react', required_level: 4, current_level: 2 },
      ],
    },
    ai_recommendations: {
      origin: 'AI',
      model: 'gemini-3.8-flash',
      generated_at: '2026-11-05T14:00:00Z',
      disclaimer: 'Sugerencia generada por IA; verificar antes de decidir.',
      items: [
        {
          type: 'course',
          skill: 'docker',
          text: 'Completar el módulo de contenedores con Docker Compose.',
          priority: 'alta',
        },
      ],
    },
  });

  return (
    <div className="min-h-screen bg-gray-50 text-gray-800 font-sans p-6">
      <header className="max-w-5xl mx-auto mb-8 border-b pb-4 flex justify-between items-center">
        <h1 className="text-2xl font-bold text-blue-900">{APP_TITLE} - MVP</h1>
        <nav className="flex space-x-4">
          <button
            onClick={() => setActiveTab('matching')}
            className={`px-3 py-2 rounded text-sm font-medium ${
              activeTab === 'matching' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'
            }`}
          >
            Matching & Scoring
          </button>
          <button
            onClick={() => setActiveTab('profile')}
            className={`px-3 py-2 rounded text-sm font-medium ${
              activeTab === 'profile' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'
            }`}
          >
            Mi Perfil (CV)
          </button>
          <button
            onClick={() => setActiveTab('auth')}
            className={`px-3 py-2 rounded text-sm font-medium ${
              activeTab === 'auth' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'
            }`}
          >
            Autenticación
          </button>
        </nav>
      </header>

      <main className="max-w-5xl mx-auto">
        {activeTab === 'matching' && (
          <section className="space-y-6">
            <h2 className="text-xl font-semibold border-b pb-2">
              Evaluación de Compatibilidad (HU-14 y HU-15)
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <RuleScoreCard data={matchData.rule_based} />
              <AISuggestionCard data={matchData.ai_recommendations} />
            </div>
          </section>
        )}

        {activeTab === 'profile' && <StudentProfile />}
        {activeTab === 'auth' && <AuthForm />}
      </main>
    </div>
  );
}