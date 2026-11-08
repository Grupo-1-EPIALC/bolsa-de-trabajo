import React, { useCallback, useEffect, useState } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { ProfileStart } from '../components/profile/ProfileStart';
import { CvImport } from '../components/profile/CvImport';
import { ProfileWizard } from '../components/profile/ProfileWizard';
import { ProfileDashboard } from '../components/profile/ProfileDashboard';
import { JobRecommendations } from '../components/matching/JobRecommendations';
import { JobBoard } from '../components/jobs/JobBoard';
import { profileService } from '../services/profileService';
import { ApiError, errorMessage } from '../services/api';
import { firstIncompleteStep } from '../profile/draft';
import type { StudentSection } from '../navigation';
import type { CvResult, ProfileStep, ProfileView } from '../types/profile';

interface StudentAreaProps {
  section: StudentSection;
  onSection: (section: StudentSection) => void;
}

type Onboarding = 'start' | 'import';

type Header = { title: string; subtitle: string; icon: string };

type StudentOnlySection = Exclude<StudentSection, 'searches' | 'users' | 'settings'>;

const HEADERS: Record<StudentOnlySection, Header> = {
  panel: {
    title: 'Mi panel',
    subtitle: 'Tus ofertas recomendadas, tu perfil y tu CV en un solo lugar.',
    icon: 'bi-grid',
  },
  recommendations: {
    title: 'Ofertas para vos',
    subtitle: 'Ordenadas por compatibilidad calculada por reglas, con consejos de la IA.',
    icon: 'bi-briefcase',
  },
  jobs: {
    title: 'Todas las ofertas',
    subtitle: 'Las búsquedas activas de todas las empresas.',
    icon: 'bi-briefcase',
  },
  profile: {
    title: 'Mi perfil',
    subtitle: 'Datos del CV, preferencias laborales y privacidad.',
    icon: 'bi-person-vcard',
  },
};

/**
 * Área del estudiante (contracts/profile_frontend.md §1):
 * sin perfil → elegir CV o carga manual · perfil incompleto → asistente en el paso pendiente ·
 * perfil listo → panel con recomendaciones, edición y descarga del CV.
 */
export const StudentArea: React.FC<StudentAreaProps> = ({ section, onSection }) => {
  const [profile, setProfile] = useState<ProfileView | null | undefined>(undefined);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [onboarding, setOnboarding] = useState<Onboarding | null>(null);
  const [cvResult, setCvResult] = useState<CvResult | null>(null);
  const [wizardStep, setWizardStep] = useState<ProfileStep>('cv');
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const openWizard = useCallback(
    (step: ProfileStep, result: CvResult | null = null) => {
      setCvResult(result);
      setWizardStep(step);
      setOnboarding(null);
      onSection('profile');
    },
    [onSection],
  );

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      const mine = await profileService.getMine();
      setProfile(mine);
      if (!mine) {
        setOnboarding('start');
      } else {
        // Perfil en borrador: retomar en el primer paso incompleto.
        const pending = firstIncompleteStep(mine.completion);
        if (pending && section === 'panel') openWizard(pending);
      }
    } catch (err) {
      setLoadError(errorMessage(err));
    }
    // Sólo al montar: después el estado se actualiza con cada guardado.
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Al navegar desde la cabecera se sale de la importación del CV (si ya hay perfil).
  useEffect(() => {
    if (profile) setOnboarding(null);
  }, [section]); // sólo cuando cambia la sección

  const startManual = async () => {
    setBusy(true);
    setActionError(null);
    try {
      setProfile(await profileService.create());
      openWizard('cv');
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const cvCompleted = async (result: CvResult) => {
    // La subida crea el perfil en borrador si no existía.
    setProfile(await profileService.getMine());
    openWizard('cv', result);
  };

  const reviewSuggestions = async () => {
    setActionError(null);
    try {
      const result = await profileService.getSuggestions();
      if (result) openWizard('cv', result);
      else setProfile((p) => (p ? { ...p, has_cv_suggestions: false } : p));
    } catch (err) {
      setActionError(errorMessage(err));
    }
  };

  // 💡 PASO 2.1: Handler inmutable para descartar sugerencias de IA de inmediato
  const discardSuggestions = async () => {
    setActionError(null); // 1. Limpiamos cualquier cartel de error previo al iniciar
    try {
      await profileService.discardSuggestions();
    } catch (err) {
      // 2. 💡 EL CERROJO DEL 404: Si el backend dice que ya no existen, lo ignoramos pacíficamente
      if (err instanceof ApiError && err.status === 404) {
        console.warn('Las sugerencias ya fueron descartadas previamente.');
      } else {
        // Solo mostramos errores reales (ej. 500, 502)
        setActionError(errorMessage(err));
        return;
      }
    }
    // 3. Forzamos el estado limpio en React para la UI
    setProfile((prev) => (prev ? { ...prev, has_cv_suggestions: false } : prev));
  };

  // Secciones de otros roles (búsquedas, cuentas, configuración) caen en el panel.
  const current: StudentOnlySection =
    section in HEADERS ? (section as StudentOnlySection) : 'panel';
  const header =
    section === 'jobs'
      ? HEADERS.jobs
      : onboarding
        ? {
            title: 'Alta de perfil',
            subtitle: 'Armá tu perfil para recibir ofertas.',
            icon: 'bi-person-plus',
          }
        : HEADERS[current];

  let content: React.ReactNode;
  if (loadError) {
    content = (
      <div
        className="alert alert-danger d-flex justify-content-between align-items-center"
        role="alert"
      >
        <span>{loadError}</span>
        <button type="button" className="btn btn-sm btn-primary btn-pill" onClick={load}>
          Reintentar
        </button>
      </div>
    );
  } else if (section === 'jobs') {
    // El listado no depende del perfil: se ve aunque todavía no lo haya cargado.
    content = <JobBoard />;
  } else if (profile === undefined) {
    content = (
      <div className="text-center py-5">
        <span
          className="spinner-border text-primary"
          role="status"
          aria-label="Cargando tu perfil"
        />
      </div>
    );
  } else if (onboarding === 'import') {
    content = (
      <CvImport
        onCompleted={cvCompleted}
        onManual={profile ? () => openWizard('cv') : startManual}
        onCancel={() => setOnboarding(profile ? null : 'start')}
      />
    );
  } else if (!profile) {
    content = (
      <ProfileStart onImportCv={() => setOnboarding('import')} onManual={startManual} busy={busy} />
    );
  } else if (section === 'profile') {
    content = (
      <ProfileWizard
        key={`${wizardStep}-${cvResult?.received_at ?? 'manual'}`}
        profile={profile}
        initialStep={wizardStep}
        cvResult={cvResult}
        // 💡 EL CERROJO: Ignora el "true" fantasma del backend en pasos posteriores
        onProfileChange={(updated) => {
          setProfile((prev) =>
            prev
              ? {
                  ...updated,
                  has_cv_suggestions:
                    prev.has_cv_suggestions === false ? false : updated.has_cv_suggestions,
                }
              : updated,
          );
        }}
        onDiscardSuggestions={discardSuggestions}
        onDone={() => {
          setCvResult(null);
          onSection('panel');
        }}
      />
    );
  } else if (section === 'recommendations') {
    content = (
      <JobRecommendations
        profileId={profile.id}
        profileComplete={profile.completion.status === 'complete'}
        onCompleteProfile={() => openWizard(firstIncompleteStep(profile.completion) ?? 'privacy')}
      />
    );
  } else {
    content = (
      <ProfileDashboard
        profile={profile}
        onRecommendations={() => onSection('recommendations')}
        onEdit={(step) => openWizard(step)}
        onReviewSuggestions={reviewSuggestions}
        onImportCv={() => setOnboarding('import')}
      />
    );
  }

  return (
    <>
      <PageHeader {...header} />
      <div className="container py-4 py-md-5">
        {actionError && (
          <div className="alert alert-danger small" role="alert">
            {actionError}
          </div>
        )}
        {content}
      </div>
    </>
  );
};
