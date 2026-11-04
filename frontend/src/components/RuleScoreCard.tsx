import React from 'react';
import { RuleBasedResult } from '../types/matching';
import { ShieldCheck, AlertCircle } from 'lucide-react';

interface Props {
  scoreData?: RuleBasedResult;
}

export const RuleScoreCard: React.FC<Props> = ({ scoreData }) => {
  if (!scoreData) {
    return (
      <div className="bg-emerald-100/40 rounded-2xl border border-emerald-300 p-6 shadow-xs">
        <p className="text-sm text-emerald-800 font-medium">Cargando puntaje por reglas...</p>
      </div>
    );
  }

  return (
    /* Fondo verde tenue bien visible (bg-emerald-100/60) con borde emerald-300 */
    <div className="w-full bg-emerald-100/50 rounded-2xl border border-emerald-300 p-5 sm:p-6 shadow-xs hover:shadow-md transition-all relative overflow-hidden">
      {/* Borde lateral verde sólido */}
      <div className="absolute top-0 left-0 w-2 h-full bg-emerald-600" />

      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <div className="flex items-center space-x-2 mb-1.5">
            {/* Badge de Encabezado equilibrado (text-xs font-bold) */}
            <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-emerald-200/80 text-emerald-900 border border-emerald-400/60 uppercase tracking-wide">
              <ShieldCheck className="w-4 h-4 mr-1.5 text-emerald-700" />
              Calculado por Reglas ({scoreData.origin})
            </span>
          </div>
          <h3 className="text-xl font-extrabold text-slate-900">Compatibilidad Auditada</h3>
          <p className="text-xs text-slate-600 mt-0.5">Motor determinístico v{scoreData.engine_version}</p>
        </div>

        {/* Score numérico compacto (text-3xl) */}
        <div className="flex flex-col items-end shrink-0">
          <div className="text-3xl sm:text-4xl font-black text-slate-900 tracking-tight">
            {scoreData.score}<span className="text-xs font-semibold text-slate-500">/100</span>
          </div>
          <span className="text-[11px] text-emerald-800 font-bold bg-emerald-200/90 px-2 py-0.5 rounded mt-0.5 border border-emerald-300">
            Verificado
          </span>
        </div>
      </div>

      {/* Desglose de Criterios (Fondo blanco interno de alto contraste) */}
      <div className="space-y-3 mb-5 bg-white/90 p-4 rounded-xl border border-emerald-200/80 shadow-xs">
        <h4 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Desglose de Criterios</h4>
        
        {scoreData.breakdown && Object.entries(scoreData.breakdown).map(([criterion, pts]) => (
          <div key={criterion} className="space-y-1">
            <div className="flex justify-between text-xs font-semibold text-slate-700">
              <span className="capitalize">{criterion.replace('_', ' ')}</span>
              <span className="text-slate-900 font-extrabold">{pts} pts</span>
            </div>
            <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden border border-slate-200/60">
              <div
                className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                style={{ width: `${Math.min((pts / 50) * 100, 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Competencias Faltantes */}
      <div>
        <h4 className="text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-2.5 flex items-center">
          <AlertCircle className="w-3.5 h-3.5 text-amber-600 mr-1.5" />
          Competencias Faltantes ({scoreData.missing_skills?.length || 0})
        </h4>

        <div className="space-y-2">
          {scoreData.missing_skills?.map((item, idx) => (
            <div key={idx} className="flex items-center justify-between p-2.5 bg-white/95 rounded-lg border border-emerald-200/70 text-xs shadow-xs">
              <div className="flex items-center space-x-2">
                <span className="w-2 h-2 rounded-full bg-amber-500" />
                <span className="font-bold text-slate-800">{item.skill}</span>
              </div>
              <span className="text-[11px] font-semibold text-slate-600 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                Brecha: nivel {item.current_level} → {item.required_level}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};