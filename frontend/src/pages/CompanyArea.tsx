import React, { useCallback, useEffect, useState } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { CompanyForm } from '../components/company/CompanyForm';
import { CompanyDashboard } from '../components/company/CompanyDashboard';
import { companyService } from '../services/companyService';
import { errorMessage } from '../services/api';
import type { StudentSection } from '../navigation';
import type { SessionUser } from '../services/session';
import type { CompanyProfile, CompanyStep } from '../types/company';

interface CompanyAreaProps {
  user: SessionUser;
  section: StudentSection;
  onSection: (section: StudentSection) => void;
}

const firstPending = (p: CompanyProfile): CompanyStep | null =>
  p.completion.steps.find((s) => !s.complete)?.step ?? null;

/**
 * Área de la empresa (contracts/company_profile_frontend.md §2):
 * sin perfil → alta precargada · borrador → formulario en el paso pendiente ·
 * completo → panel con el perfil y las búsquedas activas.
 */
export const CompanyArea: React.FC<CompanyAreaProps> = ({ user, section, onSection }) => {
  const [profile, setProfile] = useState<CompanyProfile | null | undefined>(undefined);
  const [step, setStep] = useState<CompanyStep>('company');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const edit = useCallback(
    (s: CompanyStep) => {
      setStep(s);
      onSection('profile');
    },
    [onSection],
  );

  const load = useCallback(async () => {
    setError(null);
    try {
      const mine = await companyService.getMine();
      setProfile(mine);
      const pending = mine && firstPending(mine);
      if (pending && section === 'panel') edit(pending);
    } catch (err) {
      setError(errorMessage(err));
    }
  }, []); // sólo al montar

  useEffect(() => {
    if (user.role === 'company') load();
  }, [load, user.role]);

  const create = async () => {
    setBusy(true);
    setError(null);
    try {
      setProfile(await companyService.create());
      edit('company');
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  if (user.role !== 'company') {
    return (
      <>
        <PageHeader icon="bi-gear" title="Administración" subtitle={user.email} />
        <div className="container py-5">
          <div className="card card-elevated mx-auto text-center p-4" style={{ maxWidth: '40rem' }}>
            <p className="mb-0">
              La consola de administración todavía no está disponible en el front.
            </p>
          </div>
        </div>
      </>
    );
  }

  const editing = section === 'profile' && profile;
  let content: React.ReactNode;
  if (error && profile === undefined) {
    content = (
      <div className="alert alert-danger d-flex justify-content-between align-items-center">
        <span>{error}</span>
        <button type="button" className="btn btn-sm btn-primary btn-pill" onClick={load}>
          Reintentar
        </button>
      </div>
    );
  } else if (profile === undefined) {
    content = (
      <div className="text-center py-5">
        <span
          className="spinner-border text-primary"
          role="status"
          aria-label="Cargando tu empresa"
        />
      </div>
    );
  } else if (!profile) {
    content = (
      <div className="card card-elevated mx-auto text-center" style={{ maxWidth: '40rem' }}>
        <div className="card-body p-4 p-md-5">
          <span className="icon-circle mb-3">
            <i className="bi bi-building-add" aria-hidden="true" />
          </span>
          <h2 className="h4 fw-bold">Completá el perfil de tu empresa</h2>
          <p>
            Los estudiantes van a ver tu empresa en cada búsqueda. Precargamos la razón social, la
            actividad y el email de tu cuenta.
          </p>
          {error && <div className="alert alert-danger small">{error}</div>}
          <button
            type="button"
            className="btn btn-primary btn-pill"
            onClick={create}
            disabled={busy}
          >
            {busy && <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />}
            Completar el perfil de mi empresa
          </button>
        </div>
      </div>
    );
  } else if (editing) {
    content = (
      <CompanyForm
        key={step}
        profile={profile}
        initialStep={step}
        onProfileChange={setProfile}
        onDone={() => onSection('panel')}
      />
    );
  } else {
    content = <CompanyDashboard profile={profile} onEdit={edit} />;
  }

  return (
    <>
      <PageHeader
        icon="bi-building"
        title={editing ? 'Perfil de la empresa' : (profile?.name ?? 'Mi empresa')}
        subtitle={editing ? 'Datos de la empresa y marca empleadora.' : user.email}
      />
      <div className="container py-4 py-md-5">{content}</div>
    </>
  );
};
