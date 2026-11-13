import React, { useCallback, useEffect, useState } from 'react';
import { TextField } from '../form/Fields';
import { matchingService } from '../../services/matchingService';
import { errorMessage, validationMessages } from '../../services/api';
import {
  SettingsErrors,
  SettingsForm,
  settingsToForm,
  settingsUpdate,
  validateSettings,
} from '../../admin/settings';
import type { RecommendationSettings } from '../../types/matching';

interface MatchingSettingsProps {
  onNotice: (message: string) => void;
}

const dateTime = (iso: string | null) => {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? null
    : d.toLocaleString('es-AR', { dateStyle: 'medium', timeStyle: 'short' });
};

/** Cuántas ofertas recibe cada estudiante y cuántos candidatos cada búsqueda (matching §4.5). */
export const MatchingSettings: React.FC<MatchingSettingsProps> = ({ onNotice }) => {
  const [current, setCurrent] = useState<RecommendationSettings | null>(null);
  const [form, setForm] = useState<SettingsForm | null>(null);
  const [errors, setErrors] = useState<SettingsErrors>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const settings = await matchingService.getSettings();
      setCurrent(settings);
      setForm(settingsToForm(settings));
    } catch (err) {
      setError(errorMessage(err));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!form || !current) return;
    const found = validateSettings(form, current.limits);
    setErrors(found);
    if (Object.keys(found).length) return;
    const changes = settingsUpdate(form, current);
    if (!changes) {
      onNotice('No hay cambios para guardar');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const saved = await matchingService.updateSettings(changes);
      setCurrent(saved);
      setForm(settingsToForm(saved));
      onNotice('Configuración guardada');
    } catch (err) {
      const items = validationMessages(err);
      setError(items.length ? items.join(' · ') : errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  if (error && !current) {
    return (
      <div className="alert alert-danger d-flex justify-content-between align-items-center">
        <span>{error}</span>
        <button type="button" className="btn btn-sm btn-primary btn-pill" onClick={load}>
          Reintentar
        </button>
      </div>
    );
  }
  if (!current || !form) {
    return (
      <div className="text-center py-5">
        <span
          className="spinner-border text-primary"
          role="status"
          aria-label="Cargando la configuración"
        />
      </div>
    );
  }

  const { min, max } = current.limits;
  const updated = dateTime(current.updated_at);
  const field = (key: keyof SettingsForm, label: string, hint: string) => (
    <div className="col-12 col-md-6">
      <TextField
        label={label}
        type="number"
        min={min}
        max={max}
        required
        value={form[key]}
        hint={hint}
        onChange={(v) => {
          setForm({ ...form, [key]: v });
          setErrors((e) => ({ ...e, [key]: undefined }));
        }}
      />
      {errors[key] && (
        <div className="small text-danger mt-1" role="alert">
          {errors[key]}
        </div>
      )}
    </div>
  );

  return (
    <form className="card card-elevated" onSubmit={save} noValidate>
      <div className="card-body p-4 d-grid gap-3">
        <div>
          <h2 className="h5 fw-bold mb-1">Cantidad de recomendaciones</h2>
          <p className="small text-body-secondary mb-0">
            Rige enseguida para las vistas, los rankings por reglas y los pedidos de análisis con IA
            nuevos. Valores entre {min} y {max}.
          </p>
        </div>
        <div className="row g-3">
          {field(
            'student_jobs_limit',
            'Ofertas por estudiante',
            'Cuántas ofertas ve cada estudiante en "Ofertas para vos".',
          )}
          {field(
            'company_candidates_limit',
            'Candidatos por búsqueda',
            'Cuántos candidatos ve una empresa en cada búsqueda.',
          )}
        </div>
        {error && <div className="alert alert-danger small mb-0">{error}</div>}
        <div className="alert alert-info small mb-0">
          <i className="bi bi-info-circle me-1" aria-hidden="true" />
          La configuración queda guardada y se mantiene aunque se reinicie el servicio. Los valores
          de <code>scoring_rules.yaml</code> sólo se usan la primera vez, hasta que un admin los
          cambia.
        </div>
        <div className="d-flex flex-wrap justify-content-between align-items-center gap-2">
          <span className="small text-body-secondary">
            {updated ? `Última modificación: ${updated}` : 'Valores iniciales del servicio.'}
          </span>
          <button type="submit" className="btn btn-primary btn-pill" disabled={busy}>
            {busy && <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />}
            Guardar
          </button>
        </div>
      </div>
    </form>
  );
};
