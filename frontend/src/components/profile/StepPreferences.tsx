import React, { useState } from 'react';
import { CheckGroup, SelectField, Switch, TextField } from '../form/Fields';
import {
  AVAILABILITY_START,
  CURRENCY,
  EMPLOYMENT_TYPE,
  SALARY_PERIOD,
  SALARY_VISIBILITY,
  SENIORITY,
  SHIFT,
  WORK_MODALITY,
  WORK_SCHEDULE,
} from '../../profile/labels';
import { compact } from '../../profile/draft';
import type {
  EmploymentType,
  ProfileSections,
  ProfileView,
  SalaryRange,
  Shift,
  Target,
  WorkConditions,
  WorkModality,
  WorkSchedule,
} from '../../types/profile';

interface StepPreferencesProps {
  profile: ProfileView;
  saving: boolean;
  onSave: (sections: ProfileSections) => void;
}

const num = (v: string): number | undefined => (v.trim() === '' ? undefined : Number(v));

export const StepPreferences: React.FC<StepPreferencesProps> = ({ profile, saving, onSave }) => {
  const [target, setTarget] = useState<Target>(profile.target ?? {});
  const [roles, setRoles] = useState((profile.target?.roles ?? []).join(', '));
  const [wc, setWc] = useState<WorkConditions>(profile.work_conditions ?? {});
  const [salary, setSalary] = useState<SalaryRange>({
    currency: 'ARS',
    period: 'month',
    visibility: 'on_match',
    ...profile.work_conditions?.salary,
  });
  const [errors, setErrors] = useState<string[]>([]);

  const patch = (p: Partial<WorkConditions>) => setWc((w) => ({ ...w, ...p }));
  const patchSalary = (p: Partial<SalaryRange>) => setSalary((s) => ({ ...s, ...p }));
  const hasSalaryAmount = salary.min !== undefined || salary.max !== undefined;

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const found: string[] = [];
    if (!wc.work_modality?.length) found.push('Elegí la presencialidad que aceptás.');
    if (!wc.work_schedule?.length) found.push('Elegí al menos una modalidad horaria.');
    if (!wc.employment_type?.length) found.push('Elegí al menos un tipo de empleo.');
    if (!wc.availability_start) found.push('Indicá desde cuándo podés empezar.');
    const hours = wc.weekly_hours;
    if (hours?.min !== undefined && hours.max !== undefined && hours.min > hours.max) {
      found.push('Las horas mínimas no pueden superar las máximas.');
    }
    if (!salary.to_agree && hasSalaryAmount) {
      if (salary.min === undefined) found.push('Indicá el sueldo mínimo pretendido.');
      if (salary.max !== undefined && salary.min !== undefined && salary.max < salary.min) {
        found.push('El sueldo máximo no puede ser menor al mínimo.');
      }
    }
    setErrors(found);
    if (found.length) return;

    const nextSalary: SalaryRange | undefined = salary.to_agree
      ? { to_agree: true, visibility: salary.visibility }
      : hasSalaryAmount
        ? { ...salary, to_agree: false }
        : undefined;
    const roleList = roles
      .split(',')
      .map((r) => r.trim())
      .filter(Boolean);
    onSave(
      compact({
        target: { ...target, roles: roleList, areas: target.areas ?? [] },
        work_conditions: {
          ...wc,
          hybrid_onsite_days: wc.work_modality?.includes('hybrid')
            ? wc.hybrid_onsite_days
            : undefined,
          salary: nextSalary,
        },
      }),
    );
  };

  return (
    <form onSubmit={submit} noValidate>
      {errors.length > 0 && (
        <div className="alert alert-danger small" role="alert">
          <ul className="mb-0">
            {errors.map((e) => (
              <li key={e}>{e}</li>
            ))}
          </ul>
        </div>
      )}

      <section className="mb-4">
        <h3 className="h6 fw-bold mb-3">Qué buscás</h3>
        <div className="row g-3">
          <TextField
            className="col-md-8"
            label="Puestos que te interesan"
            hint="Separalos con comas"
            placeholder="Desarrolladora backend, Analista QA"
            value={roles}
            onChange={setRoles}
          />
          <SelectField
            className="col-md-4"
            label="Seniority"
            options={SENIORITY}
            value={target.seniority}
            onChange={(v) =>
              setTarget((t) => ({ ...t, seniority: (v || undefined) as Target['seniority'] }))
            }
          />
        </div>
      </section>

      <section className="mb-4">
        <h3 className="h6 fw-bold mb-3">Condiciones de trabajo</h3>
        <div className="d-grid gap-3">
          <CheckGroup<WorkModality>
            label="Presencialidad"
            required
            options={WORK_MODALITY}
            values={wc.work_modality}
            onChange={(v) => patch({ work_modality: v })}
          />
          {wc.work_modality?.includes('hybrid') && (
            <TextField
              className="col-md-4"
              label="Días presenciales por semana (mixta)"
              type="number"
              min={0}
              max={5}
              value={wc.hybrid_onsite_days}
              onChange={(v) => patch({ hybrid_onsite_days: num(v) })}
            />
          )}
          <CheckGroup<WorkSchedule>
            label="Modalidad horaria"
            required
            options={WORK_SCHEDULE}
            values={wc.work_schedule}
            onChange={(v) => patch({ work_schedule: v })}
          />
          <CheckGroup<EmploymentType>
            label="Tipo de empleo"
            required
            options={EMPLOYMENT_TYPE}
            values={wc.employment_type}
            onChange={(v) => patch({ employment_type: v })}
          />
          <CheckGroup<Shift>
            label="Turnos disponibles"
            options={SHIFT}
            values={wc.shifts}
            onChange={(v) => patch({ shifts: v })}
          />
          <div className="row g-3">
            <SelectField
              className="col-md-4"
              label="Disponibilidad para empezar"
              required
              options={AVAILABILITY_START}
              value={wc.availability_start}
              onChange={(v) =>
                patch({
                  availability_start: (v || undefined) as WorkConditions['availability_start'],
                })
              }
            />
            <TextField
              className="col-md-2"
              label="Horas/semana mín."
              type="number"
              min={1}
              max={80}
              value={wc.weekly_hours?.min}
              onChange={(v) => patch({ weekly_hours: { ...wc.weekly_hours, min: num(v) } })}
            />
            <TextField
              className="col-md-2"
              label="Horas/semana máx."
              type="number"
              min={1}
              max={80}
              value={wc.weekly_hours?.max}
              onChange={(v) => patch({ weekly_hours: { ...wc.weekly_hours, max: num(v) } })}
            />
            <TextField
              className="col-md-4"
              label="Distancia máxima al trabajo (km)"
              type="number"
              min={0}
              value={wc.max_commute_km}
              onChange={(v) => patch({ max_commute_km: num(v) })}
            />
          </div>
          <Switch
            label="Estoy dispuesto/a a mudarme"
            checked={!!wc.willing_to_relocate}
            onChange={(v) => patch({ willing_to_relocate: v })}
          />
        </div>
      </section>

      <section className="mb-4">
        <h3 className="h6 fw-bold mb-3">Sueldo pretendido</h3>
        <div className="row g-3">
          <div className="col-12">
            <Switch
              label="A convenir (sin monto)"
              checked={!!salary.to_agree}
              onChange={(v) => patchSalary({ to_agree: v })}
            />
          </div>
          {!salary.to_agree && (
            <>
              <TextField
                className="col-md-3"
                label="Mínimo"
                type="number"
                min={0}
                value={salary.min}
                onChange={(v) => patchSalary({ min: num(v) })}
              />
              <TextField
                className="col-md-3"
                label="Máximo"
                type="number"
                min={0}
                value={salary.max}
                onChange={(v) => patchSalary({ max: num(v) })}
              />
              <SelectField
                className="col-md-2"
                label="Moneda"
                options={CURRENCY}
                value={salary.currency}
                onChange={(v) => patchSalary({ currency: (v || 'ARS') as SalaryRange['currency'] })}
              />
              <SelectField
                className="col-md-4"
                label="Período"
                options={SALARY_PERIOD}
                value={salary.period}
                onChange={(v) => patchSalary({ period: (v || 'month') as SalaryRange['period'] })}
              />
              <div className="col-12">
                <Switch
                  label="Es negociable"
                  checked={!!salary.negotiable}
                  onChange={(v) => patchSalary({ negotiable: v })}
                />
              </div>
            </>
          )}
          <SelectField
            className="col-md-6"
            label="¿Quién ve tu pretensión?"
            options={SALARY_VISIBILITY}
            value={salary.visibility}
            onChange={(v) =>
              patchSalary({ visibility: (v || 'on_match') as SalaryRange['visibility'] })
            }
          />
        </div>
      </section>

      <div className="d-flex justify-content-end">
        <button type="submit" className="btn btn-primary btn-pill" disabled={saving}>
          {saving && <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />}
          Guardar y seguir
          <i className="bi bi-arrow-right ms-2" aria-hidden="true" />
        </button>
      </div>
    </form>
  );
};
