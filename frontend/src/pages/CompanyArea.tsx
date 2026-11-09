import React, { useCallback, useEffect, useRef, useState } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { CompanyForm } from '../components/company/CompanyForm';
import { CompanyDashboard } from '../components/company/CompanyDashboard';
import { CompanySearches } from '../components/jobs/CompanySearches';
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
 * Área de la empresa (contracts/profile.md, parte B §2):
 * sin perfil → alta precargada · borrador → formulario en el paso pendiente ·
 * completo → panel con el perfil y las búsquedas activas.
 */
export const CompanyArea: React.FC<CompanyAreaProps> = ({ user, section, onSection }) => {
  const [profile, setProfile] = useState<CompanyProfile | null | undefined>(undefined);
  const [step, setStep] = useState<CompanyStep>('company');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [startWithNew, setStartWithNew] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const noticeTimer = useRef<number | undefined>(undefined);

  const showNotice = (message: string) => {
    setNotice(message);
    window.clearTimeout(noticeTimer.current);
    noticeTimer.current = window.setTimeout(() => setNotice(null), 3000);
  };

  useEffect(() => () => window.clearTimeout(noticeTimer.current), []);

  const openSearches = (createNew: boolean) => {
    setStartWithNew(createNew);
    onSection('searches');
  };

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
  } else if (section === 'searches') {
    // Las búsquedas no dependen del perfil de empresa: el snapshot sale de auth-service.
    content = (
      <CompanySearches
        key={startWithNew ? 'new' : 'list'}
        startWithNew={startWithNew}
        onNotice={showNotice}
      />
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
    content = (
      <CompanyDashboard
        profile={profile}
        onEdit={edit}
        onSearches={() => openSearches(false)}
        onNewSearch={() => openSearches(true)}
      />
    );
  }

  return (
    <>
      <PageHeader
        icon="bi-building"
        title={
          editing
            ? 'Perfil de la empresa'
            : section === 'searches'
              ? 'Búsquedas'
              : (profile?.name ?? 'Mi empresa')
        }
        subtitle={
          editing
            ? 'Datos de la empresa y marca empleadora.'
            : section === 'searches'
              ? 'Publicá, editá y cerrá tus búsquedas. Mirá los candidatos por reglas.'
              : user.email
        }
      />
      <div className="container py-4 py-md-5">
        {notice && (
          <div className="toast-floating" role="status" aria-live="polite">
            <div className="d-flex align-items-center gap-2 text-bg-success rounded-pill shadow px-4 py-2 fw-semibold small">
              <i className="bi bi-check-circle-fill" aria-hidden="true" />
              {notice}
            </div>
          </div>
        )}
        {content}
      </div>
    </>
  );
};
