import { useState } from 'react';

// Constante original de tu archivo
export const APP_TITLE = 'Bolsa de Trabajo';

// Interfaces TypeScript alineadas a las Reglas del TP2 (RF-19 / HU-14 / HU-15)
interface RuleBasedResult {
  origin: 'RULES';
  engine_version: string;
  score: number;
  breakdown: {
    required_skills: number;
    desired_skills: number;
    levels: number;
    experience: number;
    education: number;
    languages: number;
  };
  missing_skills: Array<{
    skill: string;
    required_level: number;
    current_level: number;
  }>;
}

interface AIRecommendationResult {
  origin: 'AI';
  model: string;
  generated_at: string;
  disclaimer: string;
  items: Array<{
    type: string;
    skill: string;
    text: string;
    priority: string;
  }>;
}

// Conservamos la exportación nombrada exacta que tenías en tu repositorio
export function App() {
  // Navegación de solapas de la SPA
  const [activeTab, setActiveTab] = useState<'auth' | 'profile' | 'matching'>('matching');

  // Estado con datos de prueba que reflejan la respuesta del Backend/Gateway
  const [matchData] = useState<{
    rule_based: RuleBasedResult;
    ai_recommendations: AIRecommendationResult;
  }>({
    rule_based: {
      origin: 'RULES',
      engine_version: 'scoring-1.0.0',
      score: 72.5,
      breakdown: {
        required_skills: 40.0,
        desired_skills: 7.5,
        levels: 12.0,
        experience: 8.0,
        education: 5.0,
        languages: 0.0,
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
      {/* Encabezado Principal usando la constante APP_TITLE */}
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

      {/* Vistas Dinámicas de la SPA */}
      <main className="max-w-5xl mx-auto">
        {activeTab === 'matching' && (
          <section className="space-y-6">
            <h2 className="text-xl font-semibold border-b pb-2">
              Evaluación de Compatibilidad (HU-14 y HU-15)
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Tarjeta 1: Reglas Determinísticas (Badge Verde - RULES) */}
              <div className="bg-white p-6 rounded-lg shadow-md border-l-4 border-green-500">
                <div className="flex justify-between items-center mb-4">
                  <span className="bg-green-100 text-green-800 text-xs font-bold px-3 py-1 rounded-full uppercase">
                    Calculado por reglas ({matchData.rule_based.origin})
                  </span>
                  <span className="text-xs text-gray-400">
                    v{matchData.rule_based.engine_version}
                  </span>
                </div>
                <h3 className="text-3xl font-extrabold text-gray-900 mb-2">
                  {matchData.rule_based.score} / 100
                </h3>
                <p className="text-sm text-gray-600 mb-4">
                  Puntaje matemático determinístico sin intervención de IA.
                </p>

                <div className="border-t pt-3">
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">
                    Competencias faltantes:
                  </h4>
                  <ul className="space-y-1 text-sm text-red-600">
                    {matchData.rule_based.missing_skills.map((item, idx) => (
                      <li key={idx} className="flex justify-between">
                        <span>• {item.skill}</span>
                        <span className="text-xs text-gray-500">
                          Nivel actual: {item.current_level} / Requerido: {item.required_level}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Tarjeta 2: Recomendación por IA (Badge Ámbar - AI) */}
              <div className="bg-white p-6 rounded-lg shadow-md border-l-4 border-amber-500">
                <div className="flex justify-between items-center mb-4">
                  <span className="bg-amber-100 text-amber-800 text-xs font-bold px-3 py-1 rounded-full uppercase">
                    Sugerido por IA ({matchData.ai_recommendations.origin})
                  </span>
                  <span className="text-xs text-gray-400">
                    Modelo: {matchData.ai_recommendations.model}
                  </span>
                </div>

                <div className="bg-amber-50 border-l-2 border-amber-400 p-2 mb-4">
                  <p className="text-xs text-amber-700 italic">
                    ⚠️ {matchData.ai_recommendations.disclaimer}
                  </p>
                </div>

                <h4 className="text-sm font-semibold text-gray-700 mb-2">
                  Planes de formación sugeridos:
                </h4>
                <ul className="space-y-2 text-sm">
                  {matchData.ai_recommendations.items.map((item, idx) => (
                    <li key={idx} className="bg-gray-50 p-2 rounded border">
                      <span className="font-bold text-amber-800 uppercase text-xs block">
                        Prioridad {item.priority} - {item.skill}
                      </span>
                      <p className="text-gray-700 mt-1">{item.text}</p>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </section>
        )}

        {activeTab === 'profile' && (
          <section className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold mb-4">Perfil del Estudiante (HU-07 a HU-10)</h2>
            <p className="text-gray-600 text-sm">
              Sección reservada para carga/parseo de CV (PDF/DOCX) e historial de competencias.
            </p>
          </section>
        )}

        {activeTab === 'auth' && (
          <section className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold mb-4">Autenticación (HU-01 a HU-03)</h2>
            <p className="text-gray-600 text-sm">
              Formulario de Inicio de Sesión y Registro mediante JWT.
            </p>
          </section>
        )}
      </main>
    </div>
  );
}