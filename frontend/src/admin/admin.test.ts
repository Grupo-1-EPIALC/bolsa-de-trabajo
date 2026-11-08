import { describe, expect, it } from 'vitest';
import { ApiError } from '../services/api';
import {
  adminErrorMessage,
  displayName,
  formToUpdate,
  isValidCuit,
  userActions,
  userListQuery,
  userToForm,
  validateUserForm,
} from './users';
import { settingsToForm, settingsUpdate, validateSettings } from './settings';
import type { AdminUser } from '../types/admin';
import type { RecommendationSettings } from '../types/matching';

const ADMIN_ID = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';

function user(overrides: Partial<AdminUser> = {}): AdminUser {
  return {
    id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
    email: 'rrhh@empresa.example.test',
    role: 'company',
    deleted: false,
    created_at: '2026-11-06T21:44:39.588Z',
    updated_at: '2026-11-06T21:44:40.120Z',
    email_verified_at: null,
    deleted_at: null,
    company: { legal_name: 'Empresa Ficticia S.A.', cuit: '30712345671', activity: 'Software' },
    ...overrides,
  };
}

const student = () => user({ role: 'student', email: 'persona@example.test', company: undefined });

describe('UT-FE-ADM-01 filtros del listado de cuentas', () => {
  it('omite los filtros vacíos y siempre manda el tamaño de página', () => {
    expect(userListQuery({})).toBe('?size=20');
    expect(userListQuery({ q: '   ', page: 1 })).toBe('?size=20');
  });

  it('arma rol, búsqueda, borradas y página', () => {
    const query = new URLSearchParams(
      userListQuery({ role: 'company', q: ' Ficticia ', include_deleted: true, page: 3 }).slice(1),
    );
    expect(Object.fromEntries(query)).toEqual({
      role: 'company',
      q: 'Ficticia',
      include_deleted: 'true',
      page: '3',
      size: '20',
    });
  });
});

describe('UT-FE-ADM-02 CUIT con dígito verificador', () => {
  it('acepta un CUIT válido y rechaza el dígito equivocado o el formato', () => {
    expect(isValidCuit('30712345671')).toBe(true);
    expect(isValidCuit('30712345670')).toBe(false);
    expect(isValidCuit('30-71234567-1')).toBe(false);
    expect(isValidCuit('123')).toBe(false);
  });
});

describe('UT-FE-ADM-03 edición de una cuenta', () => {
  it('valida email y, para empresas, razón social, actividad y CUIT', () => {
    const company = user();
    expect(validateUserForm(userToForm(company), company)).toEqual({});
    expect(
      validateUserForm(
        { email: 'no-es-email', legal_name: ' ', cuit: '30712345670', activity: '' },
        company,
      ),
    ).toEqual({
      email: 'Ingresá un email válido.',
      legal_name: 'La razón social es obligatoria.',
      activity: 'La actividad es obligatoria.',
      cuit: 'El CUIT no es válido (dígito verificador).',
    });
    expect(validateUserForm({ ...userToForm(company), cuit: '3071' }, company).cuit).toBe(
      'El CUIT son 11 dígitos, sin guiones.',
    );
  });

  it('a un estudiante no le pide datos de empresa', () => {
    const s = student();
    expect(validateUserForm(userToForm(s), s)).toEqual({});
  });

  it('el PATCH lleva sólo lo que cambió, con el email normalizado', () => {
    const company = user();
    expect(formToUpdate(userToForm(company), company)).toBeNull();
    expect(
      formToUpdate({ ...userToForm(company), email: '  Nuevo@Empresa.Example.TEST ' }, company),
    ).toEqual({ email: 'nuevo@empresa.example.test' });
    expect(
      formToUpdate(
        { ...userToForm(company), legal_name: 'Otra Razón S.R.L. ', cuit: '20123456786' },
        company,
      ),
    ).toEqual({ company: { legal_name: 'Otra Razón S.R.L.', cuit: '20123456786' } });
  });

  it('nunca manda datos de empresa para un estudiante', () => {
    const s = student();
    expect(formToUpdate({ ...userToForm(s), legal_name: 'X', cuit: '30712345671' }, s)).toBeNull();
  });
});

describe('UT-FE-ADM-04 acciones y mensajes', () => {
  it('el admin no puede borrarse a sí mismo y una cuenta borrada no tiene acciones', () => {
    expect(userActions(user(), ADMIN_ID)).toEqual({
      edit: true,
      resetPassword: true,
      remove: true,
      self: false,
    });
    expect(userActions(user({ id: ADMIN_ID, role: 'admin' }), ADMIN_ID)).toMatchObject({
      remove: false,
      self: true,
    });
    expect(userActions(user({ deleted: true }), ADMIN_ID)).toMatchObject({
      edit: false,
      resetPassword: false,
      remove: false,
    });
  });

  it('traduce 409 y 404; el resto usa el mensaje del servidor', () => {
    expect(adminErrorMessage(new ApiError(409, 'CONFLICT', 'x'), 'f')).toMatch(/ya están/);
    expect(adminErrorMessage(new ApiError(404, 'NOT_FOUND', 'x'), 'f')).toMatch(/ya no existe/);
    expect(adminErrorMessage(new ApiError(403, 'FORBIDDEN', 'No podés borrar'), 'f')).toBe(
      'No podés borrar',
    );
    expect(adminErrorMessage('raro', 'Falló')).toBe('Falló');
  });

  it('muestra la razón social de una empresa y el email del resto', () => {
    expect(displayName(user())).toBe('Empresa Ficticia S.A.');
    expect(displayName(student())).toBe('persona@example.test');
  });
});

describe('UT-FE-ADM-05 configuración de matching', () => {
  const current: RecommendationSettings = {
    student_jobs_limit: 5,
    company_candidates_limit: 10,
    limits: { min: 1, max: 20 },
    updated_at: '2026-11-05T14:20:00Z',
    updated_by: ADMIN_ID,
  };

  it('valida enteros dentro de los límites del servicio', () => {
    expect(validateSettings(settingsToForm(current), current.limits)).toEqual({});
    expect(
      validateSettings(
        { student_jobs_limit: '0', company_candidates_limit: '2.5' },
        current.limits,
      ),
    ).toEqual({
      student_jobs_limit: 'Un número entero entre 1 y 20.',
      company_candidates_limit: 'Un número entero entre 1 y 20.',
    });
    expect(
      validateSettings({ student_jobs_limit: '21', company_candidates_limit: '' }, current.limits),
    ).toMatchObject({
      student_jobs_limit: expect.any(String),
      company_candidates_limit: expect.any(String),
    });
  });

  it('el PATCH lleva sólo el campo que cambió', () => {
    expect(settingsUpdate(settingsToForm(current), current)).toBeNull();
    expect(
      settingsUpdate({ student_jobs_limit: '8', company_candidates_limit: '10' }, current),
    ).toEqual({ student_jobs_limit: 8 });
  });
});
