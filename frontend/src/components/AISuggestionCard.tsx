import React from 'react';
import { AIRecommendationResult } from '../types/matching';

interface Props {
  data: AIRecommendationResult;
}

// ⚠️ Asegurate de que tenga los corchetes { data }
export const AISuggestionCard: React.FC<Props> = ({ data }) => {
  return (
    <div className="bg-white p-6 rounded-lg shadow-md border-l-4 border-amber-500">
      <div className="flex justify-between items-center mb-4">
        <span className="bg-amber-100 text-amber-800 text-xs font-bold px-3 py-1 rounded-full uppercase">
          Sugerido por IA ({data.origin})
        </span>
        <span className="text-xs text-gray-400">Modelo: {data.model}</span>
      </div>

      <div className="bg-amber-50 border-l-2 border-amber-400 p-2 mb-4">
        <p className="text-xs text-amber-700 italic">
          ⚠️ {data.disclaimer}
        </p>
      </div>

      <h4 className="text-sm font-semibold text-gray-700 mb-2">
        Planes de formación sugeridos:
      </h4>
      <ul className="space-y-2 text-sm">
        {data.items.map((item, idx) => (
          <li key={idx} className="bg-gray-50 p-2 rounded border">
            <span className="font-bold text-amber-800 uppercase text-xs block">
              Prioridad {item.priority} - {item.skill}
            </span>
            <p className="text-gray-700 mt-1">{item.text}</p>
          </li>
        ))}
      </ul>
    </div>
  );
};