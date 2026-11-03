import React from 'react';
import { RuleBasedResult } from '../types/matching';

interface Props {
  data: RuleBasedResult;
}

// ⚠️ Asegurate de que tenga los corchetes { data }
export const RuleScoreCard: React.FC<Props> = ({ data }) => {
  return (
    <div className="bg-white p-6 rounded-lg shadow-md border-l-4 border-green-500">
      <div className="flex justify-between items-center mb-4">
        <span className="bg-green-100 text-green-800 text-xs font-bold px-3 py-1 rounded-full uppercase">
          Calculado por reglas ({data.origin})
        </span>
        <span className="text-xs text-gray-400">v{data.engine_version}</span>
      </div>

      <h3 className="text-3xl font-extrabold text-gray-900 mb-2">
        {data.score} / 100
      </h3>
      <p className="text-sm text-gray-600 mb-4">
        Puntaje matemático determinístico sin alucinaciones ni intervención de IA.
      </p>

      <div className="border-t pt-3">
        <h4 className="text-sm font-semibold text-gray-700 mb-2">
          Competencias faltantes:
        </h4>
        {data.missing_skills.length === 0 ? (
          <p className="text-xs text-green-600 font-medium">¡Cumple con todos los requisitos!</p>
        ) : (
          <ul className="space-y-1 text-sm text-red-600">
            {data.missing_skills.map((item, idx) => (
              <li key={idx} className="flex justify-between">
                <span>• {item.skill}</span>
                <span className="text-xs text-gray-500">
                  Nivel actual: {item.current_level} / Requerido: {item.required_level}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};