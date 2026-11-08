import React from 'react';
import { ROLE_LABELS } from '../../admin/users';
import { labelOf } from '../../profile/labels';
import type { Role } from '../../services/session';
import type { AdminUser } from '../../types/admin';

export const RoleBadge: React.FC<{ role: Role }> = ({ role }) => (
  <span
    className={`badge rounded-pill ${
      role === 'admin'
        ? 'text-bg-dark'
        : role === 'company'
          ? 'text-bg-primary'
          : 'text-bg-secondary'
    }`}
  >
    {labelOf(ROLE_LABELS, role)}
  </span>
);

export const StatusBadge: React.FC<{ user: AdminUser }> = ({ user }) =>
  user.deleted ? (
    <span className="badge rounded-pill text-bg-danger">Borrada</span>
  ) : (
    <span className="badge rounded-pill text-bg-success">Activa</span>
  );
