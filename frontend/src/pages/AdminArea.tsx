import React, { useEffect, useRef, useState } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { AdminDashboard } from '../components/admin/AdminDashboard';
import { AdminUsers } from '../components/admin/AdminUsers';
import { MatchingSettings } from '../components/admin/MatchingSettings';
import type { StudentSection } from '../navigation';
import type { Role, SessionUser } from '../services/session';

interface AdminAreaProps {
  user: SessionUser;
  section: StudentSection;
  onSection: (section: StudentSection) => void;
}

const HEADERS: Partial<Record<StudentSection, { title: string; subtitle: string; icon: string }>> =
  {
    users: {
      title: 'Cuentas',
      subtitle: 'Buscá, editá, forzá el cambio de clave o borrá cuentas de estudiantes y empresas.',
      icon: 'bi-people',
    },
    settings: {
      title: 'Configuración de matching',
      subtitle: 'Cuántas ofertas y candidatos se recomiendan.',
      icon: 'bi-sliders',
    },
  };

/**
 * Área del administrador: resumen, cuentas (contracts/auth.md, parte A §7) y
 * configuración de matching (contracts/matching.md, parte A §4.5).
 */
export const AdminArea: React.FC<AdminAreaProps> = ({ user, section, onSection }) => {
  const [roleFilter, setRoleFilter] = useState<Role | undefined>(undefined);
  const [notice, setNotice] = useState<string | null>(null);
  const noticeTimer = useRef<number | undefined>(undefined);

  const showNotice = (message: string) => {
    setNotice(message);
    window.clearTimeout(noticeTimer.current);
    noticeTimer.current = window.setTimeout(() => setNotice(null), 3000);
  };

  useEffect(() => () => window.clearTimeout(noticeTimer.current), []);

  // El filtro de rol que eligió el resumen vale sólo hasta salir de "Cuentas".
  useEffect(() => {
    if (section !== 'users') setRoleFilter(undefined);
  }, [section]);

  const header = HEADERS[section] ?? {
    title: 'Administración',
    subtitle: user.email,
    icon: 'bi-shield-lock',
  };

  let content: React.ReactNode;
  if (section === 'users') {
    content = (
      <AdminUsers
        key={roleFilter ?? 'all'}
        currentUserId={user.id}
        initialRole={roleFilter}
        onNotice={showNotice}
      />
    );
  } else if (section === 'settings') {
    content = <MatchingSettings onNotice={showNotice} />;
  } else {
    content = (
      <AdminDashboard
        onUsers={(role) => {
          setRoleFilter(role);
          onSection('users');
        }}
        onSettings={() => onSection('settings')}
      />
    );
  }

  return (
    <>
      <PageHeader icon={header.icon} title={header.title} subtitle={header.subtitle} />
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
