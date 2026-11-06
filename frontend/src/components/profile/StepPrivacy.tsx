import React, { useState } from 'react';
import { SelectField, Switch } from '../form/Fields';
import { JOB_SEARCH_STATUS, PROFILE_VISIBILITY } from '../../profile/labels';
import type { Consents, ProfileSections, ProfileView } from '../../types/profile';

interface StepPrivacyProps {
  profile: ProfileView;
  saving: boolean;
  onSave: (sections: ProfileSections) => void;
}

export const StepPrivacy: React.FC<StepPrivacyProps> = ({ profile, saving, onSave }) => {
  const [consents, setConsents] = useState<Consents>({
    data_processing: false,
    ai_processing: false,
    contact_by_email: false,
    ...profile.consents,
  });
  const [visibility, setVisibility] = useState(profile.visibility ?? 'public_to_companies');
  const [status, setStatus] = useState(profile.job_search_status ?? 'active');
  const [error, setError] = useState<string | null>(null);

  const patch = (p: Partial<Consents>) => setConsents((c) => ({ ...c, ...p }));

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!consents.data_processing) {
      setError(
        'Para usar la bolsa de trabajo necesitamos tu consentimiento para tratar tus datos.',
      );
      return;
    }
    setError(null);
    const { data_processing, ai_processing, contact_by_email } = consents;
    onSave({
      consents: { data_processing, ai_processing, contact_by_email },
      visibility,
      job_search_status: status,
    });
  };

  return (
    <form onSubmit={submit} noValidate>
      {error && (
        <div className="alert alert-danger small" role="alert">
          {error}
        </div>
      )}
      <section className="mb-4 d-grid gap-3">
        <h3 className="h6 fw-bold mb-0">Consentimientos</h3>
        <Switch
          label={
            <>
              Acepto el tratamiento de mis datos personales para la bolsa de trabajo
              <span className="text-danger ms-1">*</span>
            </>
          }
          checked={consents.data_processing}
          onChange={(v) => patch({ data_processing: v })}
        />
        <Switch
          label="Acepto que la IA analice mi perfil para darme recomendaciones"
          hint="Si no lo aceptás, igual vas a ver tu compatibilidad calculada por reglas."
          checked={consents.ai_processing}
          onChange={(v) => patch({ ai_processing: v })}
        />
        <Switch
          label="Acepto que me contacten por email"
          checked={consents.contact_by_email}
          onChange={(v) => patch({ contact_by_email: v })}
        />
      </section>

      <section className="mb-4">
        <h3 className="h6 fw-bold mb-3">Visibilidad</h3>
        <div className="row g-3">
          <SelectField
            className="col-md-6"
            label="¿Quién ve tu perfil?"
            options={PROFILE_VISIBILITY}
            value={visibility}
            hint="Sólo los perfiles visibles y buscando trabajo entran al matching."
            onChange={(v) => setVisibility((v || 'public_to_companies') as typeof visibility)}
          />
          <SelectField
            className="col-md-6"
            label="Estado de búsqueda"
            options={JOB_SEARCH_STATUS}
            value={status}
            onChange={(v) => setStatus((v || 'active') as typeof status)}
          />
        </div>
      </section>

      <div className="d-flex justify-content-end">
        <button type="submit" className="btn btn-primary btn-pill" disabled={saving}>
          {saving && <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />}
          Guardar y terminar
          <i className="bi bi-check2 ms-2" aria-hidden="true" />
        </button>
      </div>
    </form>
  );
};
