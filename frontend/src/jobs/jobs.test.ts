import { describe, expect, it } from 'vitest';
import { ApiError } from '../services/api';
import { dateLabel, jobFacts, salaryLabel } from './format';
import {
  emptyJobForm,
  endOfDayIso,
  fieldErrorsFromApi,
  formToInput,
  jobToForm,
  pendingErrors,
  validateJobForm,
  type JobForm,
} from './form';
import type { JobOpportunity } from '../types/jobs';

const NOW = new Date('2026-11-06T12:00:00Z');

function validForm(overrides: Partial<JobForm> = {}): JobForm {
  return {
    ...emptyJobForm(),
    title: 'Desarrollador/a Backend Python Jr.',
    description: 'Microservicios REST con FastAPI.',
    seniority: 'junior',
    province: 'CABA',
    city: 'Buenos Aires',
    skills: [{ name: 'Python', level: 3, kind: 'required' }],
    ...overrides,
  };
}

const JOB: JobOpportunity = {
  id: 'job-004',
  company_id: '22222222-2222-4222-8222-000000000001',
  company_snapshot: { name: 'Empresa Ficticia S.A.', industry: 'software' },
  status: 'active',
  title: 'Backend Python',
  description: 'APIs REST.',
  responsibilities: ['Implementar endpoints', 'Escribir tests'],
  area: 'desarrollo backend',
  seniority: 'junior',
  vacancies: 2,
  location: {
    country: 'AR',
    province: 'CABA',
    city: 'Buenos Aires',
    postal_code: null,
    zone: null,
  },
  work_conditions: {
    work_schedule: ['part_time'],
    work_modality: ['hybrid'],
    hybrid_onsite_days: 2,
    employment_type: ['employee'],
    contract_duration: [],
    weekly_hours: { min: 20, max: 30 },
    shifts: [],
    availability_start: 'immediate',
    salary: {
      min: 600000,
      max: 800000,
      currency: 'ARS',
      period: 'month',
      gross: true,
      visibility: 'on_match',
      to_agree: false,
      adjustment: 'quarterly',
    },
    relocation_support: true,
    driver_license: ['B1'],
    work_authorization: [],
    timezone: 'America/Argentina/Buenos_Aires',
  },
  requirements: {
    skills: [{ name: 'Python', normalized: 'python', level: 3, kind: 'required', years: null }],
    languages: [{ name: 'Inglés', normalized: 'ingles', level: 'B1', kind: 'desired' }],
    education: [{ level: 'university', status: 'in_progress', field: 'sistemas', kind: 'desired' }],
    experience: { min_years: 1, area: 'backend', kind: 'required' },
    certifications: [{ name: 'Scrum', kind: 'desired' }],
    academic: { min_progress_percent: 50, careers: [], min_current_year: null },
  },
  benefits: ['Capacitación'],
  created_at: '2026-11-05T14:00:00Z',
  updated_at: '2026-11-05T14:00:00Z',
  published_at: '2026-11-05T14:00:00Z',
  expires_at: null,
  version: 3,
};

describe('salaryLabel (§7)', () => {
  it('sueldo null es "no publicado", nunca $ 0', () => {
    expect(salaryLabel(null)).toBe('Sueldo no publicado');
    expect(salaryLabel(undefined)).toBe('Sueldo no publicado');
  });

  it('to_agree o sin montos es "A convenir"', () => {
    expect(salaryLabel({ to_agree: true, min: null, max: null })).toBe('A convenir');
    expect(salaryLabel({ currency: 'ARS' })).toBe('A convenir');
  });

  it('formatea el rango con moneda y período', () => {
    const label = salaryLabel({ min: 600000, max: 800000, currency: 'ARS', period: 'month' });
    expect(label).toMatch(/600\.000.*800\.000 por mes$/);
    expect(salaryLabel({ min: 1000, currency: 'USD', period: 'month' })).toMatch(/^Desde .*1\.000/);
    expect(salaryLabel({ max: 500, currency: 'USD', gross: false })).toMatch(/^Hasta .*\(neto\)$/);
  });
});

describe('jobFacts y dateLabel', () => {
  it('resume área, seniority, lugar y modalidad', () => {
    expect(jobFacts(JOB)).toEqual([
      'desarrollo backend',
      'Junior',
      'Buenos Aires, CABA',
      'Mixta / híbrida',
    ]);
  });

  it('fecha vacía o inválida no rompe', () => {
    expect(dateLabel(null)).toBe('');
    expect(dateLabel('no-es-fecha')).toBe('');
    expect(dateLabel('2026-11-05T14:00:00Z')).toContain('2026');
  });
});

describe('validateJobForm (§3)', () => {
  it('un formulario completo no tiene errores', () => {
    expect(validateJobForm(validForm(), NOW)).toEqual({});
  });

  it('pide título, descripción, seniority y lugar', () => {
    const errors = validateJobForm(emptyJobForm(), NOW);
    expect(Object.keys(errors).sort()).toEqual(
      ['city', 'description', 'province', 'seniority', 'skills', 'title'].sort(),
    );
  });

  it('UT-JOBS-01: al menos una competencia obligatoria', () => {
    const errors = validateJobForm(
      validForm({ skills: [{ name: 'Python', level: 3, kind: 'desired' }] }),
      NOW,
    );
    expect(errors.skills).toMatch(/obligatoria/);
  });

  it('valida horas, días híbridos, sueldo y fecha de cierre', () => {
    const errors = validateJobForm(
      validForm({
        hoursMin: '40',
        hoursMax: '20',
        hybridDays: '6',
        salaryMode: 'range',
        salaryMin: '900',
        salaryMax: '100',
        expiresAt: '2026-01-01',
      }),
      NOW,
    );
    expect(errors.hours).toMatch(/mínimo/);
    expect(errors.hybridDays).toBeDefined();
    expect(errors.salary).toMatch(/mínimo/);
    expect(errors.expiresAt).toMatch(/futura/);
  });

  it('un rango sin montos pide elegir "A convenir"', () => {
    expect(validateJobForm(validForm({ salaryMode: 'range' }), NOW).salary).toMatch(/convenir/);
  });
});

describe('formToInput', () => {
  it('no manda company_id, status, version ni timestamps (§2)', () => {
    const input = formToInput(validForm({ responsibilities: ' Uno \n\n Dos ' }));
    expect(Object.keys(input)).not.toEqual(
      expect.arrayContaining(['company_id', 'status', 'version', 'created_at']),
    );
    expect(input.responsibilities).toEqual(['Uno', 'Dos']);
    expect(input.work_conditions?.salary).toBeNull();
    expect(input.requirements.experience).toBeNull();
    expect(input.expires_at).toBeNull();
  });

  it('descarta filas de competencias vacías y arma la experiencia', () => {
    const input = formToInput(
      validForm({
        skills: [
          { name: ' Python ', level: 4, kind: 'required' },
          { name: '  ', level: 3, kind: 'desired' },
        ],
        experienceYears: '1,5',
        experienceArea: 'backend',
      }),
    );
    expect(input.requirements.skills).toEqual([{ name: 'Python', level: 4, kind: 'required' }]);
    expect(input.requirements.experience).toEqual({
      min_years: 1.5,
      area: 'backend',
      kind: 'required',
    });
  });

  it('"A convenir" viaja con min/max en null', () => {
    const input = formToInput(validForm({ salaryMode: 'to_agree', salaryVisibility: 'hidden' }));
    expect(input.work_conditions?.salary).toMatchObject({
      to_agree: true,
      min: null,
      max: null,
      visibility: 'hidden',
    });
  });

  it('al editar conserva lo que el formulario no muestra (PATCH reemplaza bloques)', () => {
    const form = jobToForm(JOB);
    form.title = 'Backend Python Semi Senior';
    form.salaryMax = '900000';
    const input = formToInput(form, JOB);
    expect(input.title).toBe('Backend Python Semi Senior');
    expect(input.work_conditions).toMatchObject({
      relocation_support: true,
      driver_license: ['B1'],
      timezone: 'America/Argentina/Buenos_Aires',
      hybrid_onsite_days: 2,
    });
    expect(input.work_conditions?.salary).toMatchObject({
      min: 600000,
      max: 900000,
      adjustment: 'quarterly',
      visibility: 'on_match',
    });
    expect(input.requirements.certifications).toEqual([{ name: 'Scrum', kind: 'desired' }]);
    expect(input.requirements.academic).toEqual(JOB.requirements.academic);
    // Sin campos de respuesta que el schema de entrada rechaza (extra="forbid").
    expect(input.requirements.skills[0]).not.toHaveProperty('normalized');
    expect(input.requirements.languages?.[0]).not.toHaveProperty('normalized');
  });

  it('ida y vuelta: precargar y guardar sin cambios conserva los datos', () => {
    const input = formToInput(jobToForm(JOB), JOB);
    expect(input.vacancies).toBe(2);
    expect(input.benefits).toEqual(['Capacitación']);
    expect(input.requirements.education).toEqual(JOB.requirements.education);
    expect(input.work_conditions?.weekly_hours).toEqual({ min: 20, max: 30 });
  });

  it('la fecha de cierre es el fin del día elegido', () => {
    const input = formToInput(validForm({ expiresAt: '2026-12-31' }));
    expect(input.expires_at).toBe(endOfDayIso('2026-12-31'));
  });

  it('sin modalidad híbrida no manda días presenciales', () => {
    const input = formToInput(validForm({ workModality: ['remote'], hybridDays: '3' }));
    expect(input.work_conditions?.hybrid_onsite_days).toBeNull();
  });
});

describe('fieldErrorsFromApi', () => {
  it('mapea loc de Pydantic a campos del formulario', () => {
    const err = new ApiError(422, 'INVALID_INPUT', 'Datos inválidos', {
      errors: [
        { loc: ['body', 'location', 'country'], msg: 'String should match pattern' },
        { loc: ['body', 'requirements', 'skills', 0, 'level'], msg: 'Input should be <= 5' },
      ],
    });
    expect(fieldErrorsFromApi(err)).toEqual({
      country: 'String should match pattern',
      skills: 'Input should be <= 5',
    });
  });

  it('mapea details.field de las reglas de negocio', () => {
    const err = new ApiError(422, 'INVALID_INPUT', 'Debe tener una obligatoria', {
      field: 'requirements.skills',
    });
    expect(fieldErrorsFromApi(err)).toEqual({ skills: 'Debe tener una obligatoria' });
  });

  it('otros errores no son de campo', () => {
    expect(fieldErrorsFromApi(new ApiError(409, 'CONFLICT', 'x'))).toEqual({});
    expect(fieldErrorsFromApi(new ApiError(422, 'INVALID_INPUT', 'Body vacío'))).toEqual({
      form: 'Body vacío',
    });
  });
});

describe('pendingErrors', () => {
  it('al corregir un campo su error desaparece y no aparecen errores nuevos', () => {
    const previous = validateJobForm(emptyJobForm(), NOW);
    const fixed = { ...emptyJobForm(), title: 'Backend Python' };
    const kept = pendingErrors(previous, fixed, NOW);
    expect(kept.title).toBeUndefined();
    expect(kept.description).toBeDefined();

    const onlyTitle = pendingErrors({ title: 'Poné un título.' }, { ...emptyJobForm() }, NOW);
    expect(Object.keys(onlyTitle)).toEqual(['title']);
  });

  it('descarta el error general del servidor al editar', () => {
    expect(pendingErrors({ form: 'Error del servidor' }, validForm(), NOW)).toEqual({});
  });
});
