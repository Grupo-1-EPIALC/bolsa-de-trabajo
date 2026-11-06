import React, { useState } from 'react';
import { StepCvData } from './StepCvData';
import { StepPreferences } from './StepPreferences';
import { StepPrivacy } from './StepPrivacy';
import { profileService } from '../../services/profileService';
import { errorMessage, validationMessages } from '../../services/api';
import { STEP_ORDER, mergeDraft } from '../../profile/draft';
import { STEP_LABEL } from '../../profile/labels';
import type { CvResult, ProfileSections, ProfileStep, ProfileView } from '../../types/profile';

interface ProfileWizardProps {
  profile: ProfileView;
  initialStep: ProfileStep;
  /** Extracción de la IA para precargar el paso 1 (opcional). */
  cvResult?: CvResult | null;
  onProfileChange: (profile: ProfileView) => void;
  onDiscardSuggestions?: () => void;
  onDone: () => void;
}

export const ProfileWizard: React.FC<ProfileWizardProps> = ({
  profile,
  initialStep,
  cvResult,
  onProfileChange,
  onDiscardSuggestions,
  onDone,
}) => {
  const [step, setStep] = useState<ProfileStep>(initialStep);
  const [useDraft, setUseDraft] = useState(!!cvResult);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<{ message: string; items: string[] } | null>(null);

  const stepIndex = STEP_ORDER.indexOf(step);
  const completed = (s: ProfileStep) =>
    profile.completion.steps.find((x) => x.step === s)?.complete ?? false;

  const goTo = (s: ProfileStep) => {
    setError(null);
    setStep(s);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const save = async (sections: ProfileSections) => {
    setSaving(true);
    setError(null);
    try {
      // 1. Limpiar las listas de propiedades calculadas por el backend (normalized, months)
      const cleanSkills = sections.skills?.map(({ normalized, ...s }: any) => ({
        ...s,
        level: Number(s.level),
        source: s.source ?? 'manual',
        confirmed: true,
      }));

      const cleanExperience = sections.experience?.map(({ months, ...x }: any) => x);
      const cleanLanguages = sections.languages?.map(({ normalized, ...l }: any) => l);

      // 2. Construir manualmente el objeto SOLO con los campos editables permitidos
      // Esto descarta automáticamente id, user_id, completion, created_at, etc.
      const rawPayload: any = {
        personal: sections.personal,
        headline: sections.headline,
        academic_status: sections.academic_status,
        target: sections.target,
        work_conditions: sections.work_conditions,
        skills: cleanSkills,
        experience: cleanExperience,
        education: sections.education,
        languages: cleanLanguages,
        certifications: sections.certifications,
        projects: sections.projects,
        links: sections.links,
        volunteering: sections.volunteering,
        references_available: sections.references_available,
        visibility: sections.visibility,
        job_search_status: sections.job_search_status,
        consents: sections.consents,
      };

      // 3. Procesar el resumen: si tiene texto lo agregamos limpio
      if (sections.summary && sections.summary.trim() !== '') {
        rawPayload.summary = sections.summary.trim();
      }

      // 4. Limpiar undefineds con JavaScript nativo (reemplaza a compact y evita errores de TS)
      const finalPayload = Object.fromEntries(
        Object.entries(rawPayload).filter(([_, v]) => v !== undefined)
      ) as ProfileSections;
      
      
      // 5. Enviar a la API
      const updated = await profileService.update(finalPayload);
      onProfileChange(updated);
      
      if (step === 'cv') setUseDraft(false);
      const next = STEP_ORDER[stepIndex + 1];
      if (next) goTo(next);
      else onDone();
      
    } catch (err) {
      setError({ message: errorMessage(err), items: validationMessages(err) });
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } finally {
      setSaving(false);
    }
  };

  const draft = useDraft ? (cvResult?.profile_draft ?? null) : null;

  return (
    <div className="card card-elevated">
      <div className="card-body p-4 p-md-5">
        {/* Pasos */}
        <ol
          className="nav nav-pills nav-fill gap-2 mb-4 list-unstyled"
          aria-label="Pasos del perfil"
        >
          {STEP_ORDER.map((s, i) => (
            <li key={s} className="nav-item">
              <button
                type="button"
                className={`nav-link w-100 ${s === step ? 'active' : ''}`}
                aria-current={s === step ? 'step' : undefined}
                onClick={() => goTo(s)}
              >
                <span className="me-2">
                  {completed(s) ? (
                    <i className="bi bi-check-circle-fill" aria-label="completo" />
                  ) : (
                    `${i + 1}.`
                  )}
                </span>
                {STEP_LABEL[s]}
              </button>
            </li>
          ))}
        </ol>

        {error && (
          <div className="alert alert-danger small" role="alert">
            <strong>{error.message}</strong>
            {error.items.length > 0 && (
              <ul className="mb-0 mt-1">
                {error.items.map((i) => (
                  <li key={i}>{i}</li>
                ))}
              </ul>
            )}
          </div>
        )}

        {step === 'cv' && draft && cvResult && (
          <div className="panel-ai rounded-3 p-3 mb-4 small">
            <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-2">
              <span className="badge badge-ai text-uppercase">
                <i className="bi bi-stars me-1" aria-hidden="true" />
                Sugerido por IA
              </span>
              <button
                type="button"
                className="btn btn-sm btn-link text-danger p-0"
                onClick={() => {
                  setUseDraft(false);
                  onDiscardSuggestions?.();
                }}
              >
                No usar estos datos
              </button>
            </div>
            <p className="mb-1">
              Precargamos el formulario con lo que detectamos en{' '}
              <strong>{cvResult.file?.filename ?? 'tu CV'}</strong>. Revisá cada dato: podés
              editarlo o quitarlo. Los campos resaltados no estaban en el CV.
            </p>
            <p className="mb-0 text-body-secondary">{cvResult.disclaimer}</p>
          </div>
        )}

        {step === 'cv' && (
          <StepCvData
            key={draft ? 'draft' : 'profile'}
            initial={mergeDraft(profile, draft)}
            reviewFields={draft ? (cvResult?.review_fields ?? []) : []}
            saving={saving}
            onSave={save}
          />
        )}
        {step === 'preferences' && (
          <StepPreferences profile={profile} saving={saving} onSave={save} />
        )}
        {step === 'privacy' && <StepPrivacy profile={profile} saving={saving} onSave={save} />}

        <div className="d-flex justify-content-between mt-4 pt-3 border-top">
          <button
            type="button"
            className="btn btn-link px-0"
            disabled={stepIndex === 0}
            onClick={() => goTo(STEP_ORDER[stepIndex - 1])}
          >
            <i className="bi bi-arrow-left me-1" aria-hidden="true" />
            Paso anterior
          </button>
          <button type="button" className="btn btn-link px-0" onClick={onDone}>
            Ir a mi panel
          </button>
        </div>
      </div>
    </div>
  );
};
