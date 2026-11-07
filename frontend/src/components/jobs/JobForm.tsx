import React, { useState } from 'react';
import { CheckGroup, ListEditor, SelectField, Switch, TextField } from '../form/Fields';
import { ApiError, errorMessage } from '../../services/api';
import { jobsService } from '../../services/jobsService';
import {
  emptyJobForm,
  fieldErrorsFromApi,
  formToInput,
  jobToForm,
  newEducation,
  newLanguage,
  newSkill,
  pendingErrors,
  validateJobForm,
  type JobForm as JobFormState,
  type JobFormErrors,
  type JobFormField,
  type SalaryMode,
} from '../../jobs/form';
import {
  AVAILABILITY_START,
  CONTRACT_DURATION,
  CURRENCY,
  EDUCATION_LEVEL,
  EDUCATION_STATUS,
  EMPLOYMENT_TYPE,
  JOB_SALARY_VISIBILITY,
  LANGUAGE_LEVEL,
  REQUIREMENT_KIND,
  SALARY_PERIOD,
  SENIORITY,
  SHIFT,
  SKILL_LEVEL,
  WORK_MODALITY,
  WORK_SCHEDULE,
  labelOf,
} from '../../profile/labels';
import type { JobOpportunity, RequirementKind } from '../../types/jobs';
import type {
  AvailabilityStart,
  Currency,
  EducationLevel,
  EducationStatus,
  LanguageLevel,
  SalaryPeriod,
  SalaryVisibility,
  Seniority,
} from '../../types/profile';

interface JobFormProps {
  /** Búsqueda a editar; sin ella es un alta. */
  job?: JobOpportunity;
  onSaved: (job: JobOpportunity, created: boolean) => void;
  onCancel: () => void;
}

const SALARY_MODES: ReadonlyArray<readonly [SalaryMode, string]> = [
  ['none', 'No publicar'],
  ['range', 'Rango'],
  ['to_agree', 'A convenir'],
];

const FieldError: React.FC<{ errors: JobFormErrors; field: JobFormField }> = ({ errors, field }) =>
  errors[field] ? (
    <div className="small text-danger mt-1" role="alert">
      <i className="bi bi-exclamation-circle me-1" aria-hidden="true" />
      {errors[field]}
    </div>
  ) : null;

const Section: React.FC<{ title: string; icon: string; children: React.ReactNode }> = ({
  title,
  icon,
  children,
}) => (
  <section className="card card-elevated">
    <div className="card-body p-4">
      <h2 className="section-title h5 mb-3">
        <i className={`bi ${icon} me-2`} aria-hidden="true" />
        {title}
      </h2>
      {children}
    </div>
  </section>
);

/** Alta y edición de una búsqueda (contracts/jobs_frontend.md §3, §4 y §11). */
export const JobForm: React.FC<JobFormProps> = ({ job, onSaved, onCancel }) => {
  const [base, setBase] = useState<JobOpportunity | undefined>(job);
  const [form, setForm] = useState<JobFormState>(() => (job ? jobToForm(job) : emptyJobForm()));
  const [errors, setErrors] = useState<JobFormErrors>({});
  const [conflict, setConflict] = useState(false);
  const [busy, setBusy] = useState(false);
  const editing = !!base;

  const set = <K extends keyof JobFormState>(key: K, value: JobFormState[K]) => {
    const next = { ...form, [key]: value };
    setForm(next);
    // Al corregir un campo su error desaparece; no se muestran errores nuevos hasta guardar.
    if (Object.keys(errors).length > 0) setErrors((prev) => pendingErrors(prev, next));
  };

  const reload = async () => {
    if (!base) return;
    setBusy(true);
    try {
      const fresh = await jobsService.get(base.id);
      setBase(fresh);
      setForm(jobToForm(fresh));
      setConflict(false);
      setErrors({});
    } catch (err) {
      setErrors({ form: errorMessage(err) });
    } finally {
      setBusy(false);
    }
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const found = validateJobForm(form);
    setErrors(found);
    setConflict(false);
    if (Object.keys(found).length > 0) {
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }
    setBusy(true);
    try {
      const input = formToInput(form, base);
      const saved = base
        ? await jobsService.update(base.id, input)
        : await jobsService.create(input);
      onSaved(saved, !base);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) setConflict(true);
      else {
        const byField = fieldErrorsFromApi(err);
        setErrors(Object.keys(byField).length ? byField : { form: errorMessage(err) });
      }
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } finally {
      setBusy(false);
    }
  };

  const errorCount = Object.keys(errors).length;
  const hybrid = form.workModality.includes('hybrid');

  return (
    <form className="d-grid gap-4" onSubmit={submit} noValidate>
      {conflict && (
        <div className="alert alert-warning d-flex flex-wrap justify-content-between align-items-center gap-2">
          <span>
            <i className="bi bi-arrow-repeat me-2" aria-hidden="true" />
            Alguien más editó esta búsqueda mientras la tenías abierta. Recargala y volvé a aplicar
            tus cambios.
          </span>
          <button
            type="button"
            className="btn btn-sm btn-warning btn-pill"
            onClick={reload}
            disabled={busy}
          >
            Recargar la búsqueda
          </button>
        </div>
      )}
      {errorCount > 0 && (
        <div className="alert alert-danger mb-0" role="alert">
          {errors.form ?? 'Revisá los campos marcados antes de guardar.'}
        </div>
      )}

      <Section title="Datos generales" icon="bi-card-text">
        <div className="row g-3">
          <div className="col-md-8">
            <TextField
              label="Título"
              required
              value={form.title}
              maxLength={200}
              onChange={(v) => set('title', v)}
              placeholder="Desarrollador/a Backend Python Jr."
            />
            <FieldError errors={errors} field="title" />
          </div>
          <div className="col-md-4">
            <SelectField
              label="Seniority"
              required
              value={form.seniority}
              options={SENIORITY}
              onChange={(v) => set('seniority', v as Seniority | '')}
            />
            <FieldError errors={errors} field="seniority" />
          </div>
          <div className="col-12">
            <TextField
              label="Descripción"
              required
              multiline
              value={form.description}
              maxLength={20000}
              onChange={(v) => set('description', v)}
            />
            <FieldError errors={errors} field="description" />
          </div>
          <div className="col-md-8">
            <TextField
              label="Área"
              value={form.area}
              maxLength={120}
              onChange={(v) => set('area', v)}
              placeholder="desarrollo backend"
            />
          </div>
          <div className="col-md-4">
            <TextField
              label="Vacantes"
              type="number"
              min={1}
              max={1000}
              value={form.vacancies}
              onChange={(v) => set('vacancies', v)}
            />
            <FieldError errors={errors} field="vacancies" />
          </div>
          <div className="col-md-2">
            <TextField
              label="País"
              required
              value={form.country}
              maxLength={2}
              onChange={(v) => set('country', v.toUpperCase())}
              hint="ISO (AR)"
            />
            <FieldError errors={errors} field="country" />
          </div>
          <div className="col-md-5">
            <TextField
              label="Provincia"
              required
              value={form.province}
              maxLength={120}
              onChange={(v) => set('province', v)}
            />
            <FieldError errors={errors} field="province" />
          </div>
          <div className="col-md-5">
            <TextField
              label="Ciudad"
              required
              value={form.city}
              maxLength={120}
              onChange={(v) => set('city', v)}
            />
            <FieldError errors={errors} field="city" />
          </div>
          <div className="col-md-6">
            <TextField
              label="Responsabilidades"
              multiline
              value={form.responsibilities}
              onChange={(v) => set('responsibilities', v)}
              hint="Una por línea."
            />
          </div>
          <div className="col-md-6">
            <TextField
              label="Beneficios"
              multiline
              value={form.benefits}
              onChange={(v) => set('benefits', v)}
              hint="Uno por línea."
            />
          </div>
          <div className="col-md-4">
            <TextField
              label="Fecha de cierre"
              type="date"
              value={form.expiresAt}
              onChange={(v) => set('expiresAt', v)}
              hint="Opcional."
            />
            <FieldError errors={errors} field="expiresAt" />
          </div>
        </div>
      </Section>

      <Section title="Condiciones" icon="bi-briefcase">
        <div className="row g-3">
          <CheckGroup
            className="col-md-6"
            label="Modalidad"
            values={form.workModality}
            options={WORK_MODALITY}
            onChange={(v) => set('workModality', v)}
          />
          <CheckGroup
            className="col-md-6"
            label="Jornada"
            values={form.workSchedule}
            options={WORK_SCHEDULE}
            onChange={(v) => set('workSchedule', v)}
          />
          {hybrid && (
            <div className="col-md-4">
              <TextField
                label="Días presenciales por semana"
                type="number"
                min={0}
                max={5}
                value={form.hybridDays}
                onChange={(v) => set('hybridDays', v)}
              />
              <FieldError errors={errors} field="hybridDays" />
            </div>
          )}
          <div className="col-md-4">
            <TextField
              label="Horas semanales (mínimo)"
              type="number"
              min={0}
              max={168}
              value={form.hoursMin}
              onChange={(v) => set('hoursMin', v)}
            />
          </div>
          <div className="col-md-4">
            <TextField
              label="Horas semanales (máximo)"
              type="number"
              min={0}
              max={168}
              value={form.hoursMax}
              onChange={(v) => set('hoursMax', v)}
            />
            <FieldError errors={errors} field="hours" />
          </div>
          <CheckGroup
            className="col-md-6"
            label="Contratación"
            values={form.employmentType}
            options={EMPLOYMENT_TYPE}
            onChange={(v) => set('employmentType', v)}
          />
          <CheckGroup
            className="col-md-6"
            label="Duración"
            values={form.contractDuration}
            options={CONTRACT_DURATION}
            onChange={(v) => set('contractDuration', v)}
          />
          <CheckGroup
            className="col-md-8"
            label="Turnos"
            values={form.shifts}
            options={SHIFT}
            onChange={(v) => set('shifts', v)}
          />
          <div className="col-md-4">
            <SelectField
              label="Inicio"
              value={form.availabilityStart}
              options={AVAILABILITY_START}
              onChange={(v) => set('availabilityStart', v as AvailabilityStart | '')}
            />
          </div>
          <FieldError errors={errors} field="workConditions" />
        </div>

        <h3 className="h6 fw-bold mt-4">Sueldo</h3>
        <div className="row g-3">
          <div className="col-12">
            <div className="btn-group" role="group" aria-label="Sueldo">
              {SALARY_MODES.map(([mode, label]) => (
                <React.Fragment key={mode}>
                  <input
                    type="radio"
                    className="btn-check"
                    name="salary-mode"
                    id={`salary-${mode}`}
                    checked={form.salaryMode === mode}
                    onChange={() => set('salaryMode', mode)}
                  />
                  <label className="btn btn-sm btn-outline-primary" htmlFor={`salary-${mode}`}>
                    {label}
                  </label>
                </React.Fragment>
              ))}
            </div>
          </div>
          {form.salaryMode === 'range' && (
            <>
              <div className="col-md-3">
                <TextField
                  label="Mínimo"
                  type="number"
                  min={0}
                  value={form.salaryMin}
                  onChange={(v) => set('salaryMin', v)}
                />
              </div>
              <div className="col-md-3">
                <TextField
                  label="Máximo"
                  type="number"
                  min={0}
                  value={form.salaryMax}
                  onChange={(v) => set('salaryMax', v)}
                />
              </div>
            </>
          )}
          {form.salaryMode !== 'none' && (
            <>
              <div className="col-md-2">
                <SelectField
                  label="Moneda"
                  value={form.currency}
                  options={CURRENCY}
                  onChange={(v) => set('currency', (v || 'ARS') as Currency)}
                />
              </div>
              <div className="col-md-4">
                <SelectField
                  label="Período"
                  value={form.period}
                  options={SALARY_PERIOD}
                  onChange={(v) => set('period', (v || 'month') as SalaryPeriod)}
                />
              </div>
              <div className="col-md-6">
                <SelectField
                  label="¿Quién ve el sueldo?"
                  value={form.salaryVisibility}
                  options={JOB_SALARY_VISIBILITY}
                  onChange={(v) => set('salaryVisibility', (v || 'public') as SalaryVisibility)}
                  hint="El motor de matching lo usa siempre, aunque esté oculto."
                />
              </div>
              <div className="col-md-6 d-flex align-items-end">
                <Switch
                  label="Montos brutos"
                  checked={form.gross}
                  onChange={(v) => set('gross', v)}
                />
              </div>
            </>
          )}
          <div className="col-12">
            <FieldError errors={errors} field="salary" />
          </div>
        </div>
      </Section>

      <Section title="Requisitos" icon="bi-list-check">
        <ListEditor
          title="Competencias"
          required
          items={form.skills}
          onChange={(v) => set('skills', v)}
          newItem={newSkill}
          addLabel="Agregar competencia"
          badge={(s) => (
            <span className="badge text-bg-light border">{labelOf(REQUIREMENT_KIND, s.kind)}</span>
          )}
          render={(s, update) => (
            <div className="row g-2">
              <TextField
                className="col-md-5"
                label="Competencia"
                value={s.name}
                maxLength={120}
                onChange={(v) => update({ name: v })}
              />
              <SelectField
                className="col-md-4"
                label="Nivel pedido"
                value={s.level}
                options={SKILL_LEVEL}
                onChange={(v) => update({ level: Number(v) || 1 })}
              />
              <SelectField
                className="col-md-3"
                label="Tipo"
                value={s.kind}
                options={REQUIREMENT_KIND}
                onChange={(v) => update({ kind: (v || 'required') as RequirementKind })}
              />
            </div>
          )}
        />
        <FieldError errors={errors} field="skills" />
        <p className="small text-body-secondary">
          Al menos una obligatoria. Si falta una <strong>excluyente</strong>, el puntaje del
          candidato no pasa de 40.
        </p>

        <ListEditor
          title="Idiomas"
          items={form.languages}
          onChange={(v) => set('languages', v)}
          newItem={newLanguage}
          addLabel="Agregar idioma"
          emptyText="Sin idiomas pedidos."
          render={(l, update) => (
            <div className="row g-2">
              <TextField
                className="col-md-5"
                label="Idioma"
                value={l.name}
                maxLength={80}
                onChange={(v) => update({ name: v })}
              />
              <SelectField
                className="col-md-4"
                label="Nivel"
                value={l.level}
                options={LANGUAGE_LEVEL}
                onChange={(v) => update({ level: v as LanguageLevel | '' })}
              />
              <SelectField
                className="col-md-3"
                label="Tipo"
                value={l.kind}
                options={REQUIREMENT_KIND}
                onChange={(v) => update({ kind: (v || 'desired') as RequirementKind })}
              />
            </div>
          )}
        />
        <FieldError errors={errors} field="languages" />

        <ListEditor
          title="Formación"
          items={form.education}
          onChange={(v) => set('education', v)}
          newItem={newEducation}
          addLabel="Agregar formación"
          emptyText="Sin formación pedida."
          render={(e, update) => (
            <div className="row g-2">
              <SelectField
                className="col-md-3"
                label="Nivel"
                value={e.level}
                options={EDUCATION_LEVEL}
                onChange={(v) => update({ level: v as EducationLevel | '' })}
              />
              <SelectField
                className="col-md-3"
                label="Estado"
                value={e.status}
                options={EDUCATION_STATUS}
                onChange={(v) => update({ status: v as EducationStatus | '' })}
              />
              <TextField
                className="col-md-3"
                label="Campo"
                value={e.field}
                maxLength={120}
                onChange={(v) => update({ field: v })}
                placeholder="sistemas"
              />
              <SelectField
                className="col-md-3"
                label="Tipo"
                value={e.kind}
                options={REQUIREMENT_KIND}
                onChange={(v) => update({ kind: (v || 'desired') as RequirementKind })}
              />
            </div>
          )}
        />
        <FieldError errors={errors} field="education" />

        <h3 className="h6 fw-bold">Experiencia</h3>
        <div className="row g-2">
          <TextField
            className="col-md-3"
            label="Años mínimos"
            type="number"
            min={0}
            max={60}
            value={form.experienceYears}
            onChange={(v) => set('experienceYears', v)}
            hint="Vacío = sin mínimo."
          />
          <TextField
            className="col-md-6"
            label="Área"
            value={form.experienceArea}
            maxLength={120}
            onChange={(v) => set('experienceArea', v)}
          />
          <SelectField
            className="col-md-3"
            label="Tipo"
            value={form.experienceKind}
            options={REQUIREMENT_KIND}
            onChange={(v) => set('experienceKind', (v || 'required') as RequirementKind)}
          />
        </div>
        <FieldError errors={errors} field="experience" />
      </Section>

      <div className="d-flex flex-wrap justify-content-end gap-2">
        <button
          type="button"
          className="btn btn-outline-primary btn-pill"
          onClick={onCancel}
          disabled={busy}
        >
          Cancelar
        </button>
        <button type="submit" className="btn btn-primary btn-pill" disabled={busy}>
          {busy && <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />}
          {editing ? 'Guardar cambios' : 'Publicar búsqueda'}
        </button>
      </div>
    </form>
  );
};
