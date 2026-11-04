import React from 'react';
import { AIRecommendations } from '../types/matching';
import { Sparkles, Bot, Info, BookOpen } from 'lucide-react';

interface Props {
  aiData?: AIRecommendations;
}

export const AISuggestionCard: React.FC<Props> = ({ aiData }) => {
  if (!aiData) {
    return (
      <div className="bg-amber-100/40 rounded-2xl border border-amber-300 p-6 shadow-xs">
        <p className="text-sm text-amber-900 font-medium">Cargando sugerencias de la IA...</p>
      </div>
    );
  }

  return (
    /* Fondo ámbar tenue bien visible (bg-amber-100/60) con borde amber-300 */
    <div className="w-full bg-amber-200/40 rounded-2xl border border-amber-300 p-5 sm:p-6 shadow-xs hover:shadow-md transition-all relative overflow-hidden">
      {/* Borde lateral ámbar sólido */}
      <div className="absolute top-0 left-0 w-2 h-full bg-amber-500" />

      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <div className="flex items-center space-x-2 mb-1.5">
            {/* Badge de Encabezado equilibrado (text-xs font-bold) */}
            <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-amber-200/90 text-amber-950 border border-amber-400/60 uppercase tracking-wide">
              <Sparkles className="w-4 h-4 mr-1.5 text-amber-700" />
              Sugerido por IA ({aiData.origin})
            </span>
          </div>
          <h3 className="text-xl font-extrabold text-slate-900">Recomendaciones de Formación</h3>
          <p className="text-xs text-slate-600 mt-0.5">Modelo: {aiData.model}</p>
        </div>

        <div className="p-2 bg-amber-200/80 text-amber-900 rounded-xl border border-amber-300/80 shrink-0">
          <Bot className="w-6 h-6" />
        </div>
      </div>

      {/* Listado de Sugerencias de IA */}
      <div className="space-y-3 mb-4">
        {aiData.items?.map((item, idx) => (
          <div
            key={idx}
            className="p-3 bg-white/95 border border-amber-200/80 rounded-xl shadow-xs transition-all hover:border-amber-400"
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-amber-950 bg-amber-200/70 px-2 py-0.5 rounded flex items-center">
                <BookOpen className="w-3 h-3 mr-1" />
                {item.type}
              </span>
              {item.skill && (
                <span className="text-xs font-extrabold text-slate-800 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                  {item.skill}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-700 leading-relaxed font-medium">{item.text}</p>
          </div>
        ))}
      </div>

      {/* Disclaimer Requerido por el TP2 */}
      <div className="flex items-start space-x-2.5 p-3 bg-white/90 rounded-xl border border-amber-200/80 text-[11px] text-slate-600 leading-normal shadow-xs">
        <Info className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
        <span className="font-medium">{aiData.disclaimer}</span>
      </div>
    </div>
  );
};