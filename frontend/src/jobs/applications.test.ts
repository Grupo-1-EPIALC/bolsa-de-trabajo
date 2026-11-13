import { describe, expect, it } from 'vitest';
import { ApiError } from '../services/api';
import {
  applicantsByProfile,
  appliedJobIds,
  applicationErrorMessage,
  rankByProfile,
} from './applications';
import type { Applicant } from '../types/jobs';
import type { CompanyRuleItem } from '../types/matching';

const applicant = (profile_id: string): Applicant => ({
  id: `app-${profile_id}`,
  job_id: 'job-001',
  profile_id,
  headline: 'Estudiante de Sistemas',
  contact: {
    name: 'Persona Ficticia',
    email: 'persona@example.test',
    phone: null,
  },
  applied_at: '2026-11-13T15:00:00Z',
  updated_at: '2026-11-13T15:00:00Z',
});

describe('postulaciones', () => {
  it('arma el conjunto de ofertas a las que se postuló', () => {
    const ids = appliedJobIds({
      total: 2,
      items: [
        {
          id: 'a1',
          job_id: 'job-001',
          applied_at: '2026-11-13T15:00:00Z',
          job: null,
        },
        {
          id: 'a2',
          job_id: 'job-002',
          applied_at: '2026-11-13T15:00:00Z',
          job: null,
        },
      ],
    });
    expect(ids.has('job-001')).toBe(true);
    expect(ids.has('job-003')).toBe(false);
  });

  it('traduce los errores de la postulación', () => {
    expect(
      applicationErrorMessage(new ApiError(409, 'PROFILE_REQUIRED', 'Completá tu perfil')),
    ).toMatch(/Completá tu perfil/);
    expect(applicationErrorMessage(new ApiError(404, 'NOT_FOUND', 'Oferta no encontrada'))).toBe(
      'Esta oferta ya no está disponible.',
    );
  });

  it('cruza postulados con el ranking por profile_id', () => {
    const byProfile = applicantsByProfile([applicant('prof-1'), applicant('prof-2')]);
    expect(byProfile.get('prof-2')?.contact.email).toBe('persona@example.test');
    expect(byProfile.has('prof-9')).toBe(false);

    const ranking = rankByProfile([
      {
        rank: 1,
        candidate: { profile_id: 'prof-2' },
        match: { score: 81 },
      } as CompanyRuleItem,
    ]);
    expect(ranking.get('prof-2')?.rank).toBe(1);
    expect(ranking.has('prof-1')).toBe(false);
  });
});
