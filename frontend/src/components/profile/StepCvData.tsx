import React, { useState } from 'react';
import { CheckGroup, ListEditor, SelectField, TextField } from '../form/Fields';
import {
  EDUCATION_LEVEL,
  EDUCATION_STATUS,
  LANGUAGE_LEVEL,
  LINK_TYPE,
  SHIFT,
  SKILL_CATEGORY,
  SKILL_LEVEL,
} from '../../profile/labels';
import { compact, findPlaceholders, reviewKey } from '../../profile/draft';
import type {
  AcademicStatus,
  CertificationItem,
  EducationItem,
  ExperienceItem,
  LanguageItem,
  LinkItem,
  Personal,
  ProfileSections,
  Shift,
  SkillItem,
} from '../../types/profile';

interface StepCvDataProps {
  initial: ProfileSections;
  reviewFields: string[];
  saving: boolean;
  onSave: (sections: ProfileSections) => void;
}

const AiBadge: React.FC<{ show?: boolean }> = ({ show }) =>
  show ? (
    <span className="badge badge-ai">
      <i className="bi bi-stars me-1" aria-hidden="true" />
      Sugerido por IA
    </span>
  ) : null;

const num = (v: string): number | undefined => (v.trim() === '' ? undefined : Number(v));

/** Validaciones mínimas del paso 1 (el servicio valida todo de nuevo). */
function validate(form: ProfileSections): string[] {
  const errors: string[] = [];
  const p = form.personal;
  if (!p?.name || p.name.trim().length < 2) errors.push('Ingresá tu nombre y apellido.');
  if (!p?.email) errors.push('Ingresá tu email.');
  if (!p?.location?.country || !p.location.province || !p.location.city) {
    errors.push('Completá país, provincia y ciudad.');
  }
  if (p?.location?.country && !/^[A-Z]{2}$/.test(p.location.country)) {
    errors.push('El país va con el código de 2 letras (ej. AR).');
  }
  form.skills?.forEach((s, i) => {
    if (!s.name.trim()) errors.push(`Competencia ${i + 1}: falta el nombre.`);
    if (!(s.level >= 1 && s.level <= 5)) errors.push(`Competencia "${s.name}": elegí el nivel.`);
  });
  form.experience?.forEach((x, i) => {
    if (!x.company || !x.role || !x.start) {
      errors.push(`Experiencia ${i + 1}: completá empresa, puesto y fecha de inicio.`);
    }
  });
  form.education?.forEach((e, i) => {
    if (!e.institution || !e.degree || !e.level || !e.status) {
      errors.push(`Educación ${i + 1}: completá institución, título, nivel y estado.`);
    }
  });
  form.languages?.forEach((l, i) => {
    if (!l.name || !l.level) errors.push(`Idioma ${i + 1}: completá idioma y nivel.`);
  });
  form.links?.forEach((l, i) => {
    if (!/^https?:\/\//.test(l.url)) errors.push(`Link ${i + 1}: la URL empieza con https://`);
  });
  const left = findPlaceholders(form);
  if (left.length) errors.push(`Quedan datos por completar: ${left.join(', ')}.`);
  return errors;
}

export const StepCvData: React.FC<StepCvDataProps> = ({
  initial,
  reviewFields,
  saving,
  onSave,
}) => {
  const [form, setForm] = useState<ProfileSections>(() => ({
    ...initial,
    personal: {
      name: '',
      email: '',
      ...initial.personal,
      location: { country: 'AR', province: '', city: '', ...initial.personal?.location },
    },
    academic_status: initial.academic_status ?? {},
    skills: initial.skills ?? [],
    experience: initial.experience ?? [],
    education: initial.education ?? [],
    languages: initial.languages ?? [],
    certifications: initial.certifications ?? [],
    links: initial.links ?? [],
  }));
  const [errors, setErrors] = useState<string[]>([]);
  const review = new Set(reviewFields.map(reviewKey));
  const isReview = (key: string) => review.has(key);

  const personal = form.personal as Personal;
  const location = personal.location!;
  const academic = form.academic_status as AcademicStatus;

  const setPersonal = (patch: Partial<Personal>) =>
    setForm((f) => ({ ...f, personal: { ...(f.personal as Personal), ...patch } }));
  const setLocation = (patch: Partial<NonNullable<Personal['location']>>) =>
    setPersonal({ location: { ...location, ...patch } });
  const setAcademic = (patch: Partial<AcademicStatus>) =>
    setForm((f) => ({ ...f, academic_status: { ...f.academic_status, ...patch } }));
  const setList =
    <K extends keyof ProfileSections>(key: K) =>
    (items: ProfileSections[K]) =>
      setForm((f) => ({ ...f, [key]: items }));

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const found = validate(form);
    setErrors(found);
    if (found.length) {
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    // 1. Sanitizar skills (eliminar `normalized` para que Pydantic no rebote)
    const skills = (form.skills ?? []).map(({ normalized, ...s }) => ({
      ...s,
      level: Number(s.level),
      source: s.source ?? 'manual',
      confirmed: true,
    }));

    // 2. Sanitizar experiencia (eliminar `months` calculado)
    const experience = (form.experience ?? []).map(({ months, ...x }) => x);

    // 3. Sanitizar idiomas (eliminar `normalized`)
    const languages = (form.languages ?? []).map(({ normalized, ...l }) => l);

    // 4. Asegurar que summary viaje limpio si el usuario escribió algo
    const cleanPayload = compact({
      ...form,
      skills,
      experience,
      languages,
    });
    
    if (form.summary && form.summary.trim() !== '') {
      cleanPayload.summary = form.summary.trim();
    }

    onSave(cleanPayload);
  };

  return (
    <form onSubmit={submit} noValidate>
      {errors.length > 0 && (
        <div className="alert alert-danger small" role="alert">
          <strong>Revisá estos datos:</strong>
          <ul className="mb-0 mt-1">
            {errors.map((e) => (
              <li key={e}>{e}</li>
            ))}
          </ul>
        </div>
      )}

      <section className="mb-4">
        <h3 className="h6 fw-bold mb-3">Datos personales</h3>
        <div className="row g-3">
          <TextField
            className="col-md-6"
            label="Nombre y apellido"
            required
            value={personal.name}
            review={isReview('personal.name')}
            autoComplete="name"
            onChange={(v) => setPersonal({ name: v })}
          />
          <TextField
            className="col-md-6"
            label="Email"
            type="email"
            required
            value={personal.email}
            review={isReview('personal.email')}
            autoComplete="email"
            onChange={(v) => setPersonal({ email: v })}
          />
          <TextField
            className="col-md-4"
            label="Teléfono"
            value={personal.phone}
            review={isReview('personal.phone')}
            placeholder="+54 11 5555-0000"
            autoComplete="tel"
            onChange={(v) => setPersonal({ phone: v })}
          />
          <TextField
            className="col-md-2"
            label="País"
            required
            value={location.country}
            hint="Código de 2 letras"
            maxLength={2}
            review={isReview('personal.location.country')}
            onChange={(v) => setLocation({ country: v.toUpperCase() })}
          />
          <TextField
            className="col-md-3"
            label="Provincia"
            required
            value={location.province}
            review={isReview('personal.location.province') || isReview('personal.location')}
            onChange={(v) => setLocation({ province: v })}
          />
          <TextField
            className="col-md-3"
            label="Ciudad"
            required
            value={location.city}
            review={isReview('personal.location.city') || isReview('personal.location')}
            onChange={(v) => setLocation({ city: v })}
          />
        </div>
      </section>

      <section className="mb-4">
        <h3 className="h6 fw-bold mb-3">Perfil profesional</h3>
        <div className="row g-3">
          <TextField
            className="col-12"
            label="Título del perfil"
            value={form.headline}
            maxLength={140}
            placeholder="Estudiante de Sistemas · Backend Python"
            review={isReview('headline')}
            onChange={(v) => setForm((f) => ({ ...f, headline: v }))}
          />
          <TextField
            className="col-12"
            label="Resumen"
            required
            multiline
            maxLength={2000}
            value={form.summary === 'COMPLETAR_MANUALMENTE' ? '' : (form.summary || '')}
            review={isReview('summary')}
            onChange={(v) => setForm((f) => ({ ...f, summary: v }))}
          />
        </div>
      </section>

      <section className="mb-4">
        <h3 className="h6 fw-bold mb-3">Situación académica</h3>
        <div className="row g-3">
          <TextField
            className="col-md-6"
            label="Institución"
            value={academic.institution}
            review={isReview('academic_status.institution')}
            onChange={(v) => setAcademic({ institution: v })}
          />
          <TextField
            className="col-md-6"
            label="Carrera"
            value={academic.career}
            review={isReview('academic_status.career')}
            onChange={(v) => setAcademic({ career: v })}
          />
          <TextField
            className="col-md-3"
            label="Año que cursás"
            type="number"
            min={1}
            max={8}
            value={academic.current_year}
            onChange={(v) => setAcademic({ current_year: num(v) })}
          />
          <TextField
            className="col-md-3"
            label="Avance (%)"
            type="number"
            min={0}
            max={100}
            value={academic.progress_percent}
            onChange={(v) => setAcademic({ progress_percent: num(v) })}
          />
          <CheckGroup<Shift>
            className="col-md-6"
            label="Turno en el que cursás"
            options={SHIFT}
            values={academic.student_shift}
            onChange={(v) => setAcademic({ student_shift: v })}
          />
        </div>
      </section>

      <ListEditor<SkillItem>
        title="Competencias"
        required
        review={isReview('skills')}
        items={form.skills ?? []}
        onChange={setList('skills')}
        addLabel="Agregar competencia"
        newItem={() => ({ name: '', level: 0, source: 'manual', confirmed: true })}
        badge={(s) => <AiBadge show={s.source === 'cv_ai'} />}
        render={(s, update, i) => (
          <div className="row g-2">
            <TextField
              className="col-md-5"
              label="Competencia"
              value={s.name}
              review={isReview(`skills.${i}.name`)}
              onChange={(v) => update({ name: v })}
            />
            <SelectField
              className="col-md-4"
              label="Nivel"
              options={SKILL_LEVEL}
              value={s.level || ''}
              review={isReview(`skills.${i}.level`) || !s.level}
              onChange={(v) => update({ level: Number(v) })}
            />
            <SelectField
              className="col-md-3"
              label="Tipo"
              options={SKILL_CATEGORY}
              value={s.category}
              onChange={(v) => update({ category: (v || undefined) as SkillItem['category'] })}
            />
          </div>
        )}
      />

      <ListEditor<ExperienceItem>
        title="Experiencia"
        items={form.experience ?? []}
        onChange={setList('experience')}
        addLabel="Agregar experiencia"
        emptyText="Si todavía no trabajaste, podés dejarlo vacío."
        newItem={() => ({ company: '', role: '', start: '', end: 'actual' })}
        render={(x, update, i) => (
          <div className="row g-2">
            <TextField
              className="col-md-6"
              label="Empresa"
              value={x.company}
              review={isReview(`experience.${i}.company`)}
              onChange={(v) => update({ company: v })}
            />
            <TextField
              className="col-md-6"
              label="Puesto"
              value={x.role}
              review={isReview(`experience.${i}.role`)}
              onChange={(v) => update({ role: v })}
            />
            <TextField
              className="col-md-3"
              label="Desde"
              type="month"
              value={x.start}
              review={isReview(`experience.${i}.start`)}
              onChange={(v) => update({ start: v })}
            />
            <TextField
              className="col-md-3"
              label="Hasta"
              type="month"
              value={x.end === 'actual' ? '' : x.end}
              hint={x.end === 'actual' ? 'Trabajo actual' : undefined}
              onChange={(v) => update({ end: v || 'actual' })}
            />
            <div className="col-md-6 d-flex align-items-end">
              <div className="form-check mb-2">
                <input
                  id={`exp-current-${i}`}
                  type="checkbox"
                  className="form-check-input"
                  checked={x.end === 'actual'}
                  onChange={(e) => update({ end: e.target.checked ? 'actual' : '' })}
                />
                <label htmlFor={`exp-current-${i}`} className="form-check-label">
                  Trabajo acá actualmente
                </label>
              </div>
            </div>
            <TextField
              className="col-12"
              label="Descripción"
              multiline
              maxLength={4000}
              value={x.description}
              onChange={(v) => update({ description: v })}
            />
          </div>
        )}
      />

      <ListEditor<EducationItem>
        title="Educación"
        required
        review={isReview('education')}
        items={form.education ?? []}
        onChange={setList('education')}
        addLabel="Agregar estudio"
        newItem={() => ({
          institution: '',
          degree: '',
          level: '' as EducationItem['level'],
          status: '' as EducationItem['status'],
        })}
        render={(e, update, i) => (
          <div className="row g-2">
            <TextField
              className="col-md-6"
              label="Institución"
              value={e.institution}
              review={isReview(`education.${i}.institution`)}
              onChange={(v) => update({ institution: v })}
            />
            <TextField
              className="col-md-6"
              label="Título"
              value={e.degree}
              review={isReview(`education.${i}.degree`)}
              onChange={(v) => update({ degree: v })}
            />
            <SelectField
              className="col-md-3"
              label="Nivel"
              options={EDUCATION_LEVEL}
              value={e.level}
              review={isReview(`education.${i}.level`)}
              onChange={(v) => update({ level: v as EducationItem['level'] })}
            />
            <SelectField
              className="col-md-3"
              label="Estado"
              options={EDUCATION_STATUS}
              value={e.status}
              review={isReview(`education.${i}.status`)}
              onChange={(v) => update({ status: v as EducationItem['status'] })}
            />
            <TextField
              className="col-md-3"
              label="Inicio (año)"
              value={e.start}
              placeholder="2022"
              onChange={(v) => update({ start: v })}
            />
            <TextField
              className="col-md-3"
              label="Fin (año)"
              value={e.end}
              placeholder="2026"
              onChange={(v) => update({ end: v })}
            />
          </div>
        )}
      />

      <ListEditor<LanguageItem>
        title="Idiomas"
        items={form.languages ?? []}
        onChange={setList('languages')}
        addLabel="Agregar idioma"
        newItem={() => ({ name: '', level: '' as LanguageItem['level'] })}
        render={(l, update, i) => (
          <div className="row g-2">
            <TextField
              className="col-md-7"
              label="Idioma"
              value={l.name}
              review={isReview(`languages.${i}.name`)}
              onChange={(v) => update({ name: v })}
            />
            <SelectField
              className="col-md-5"
              label="Nivel (MCER)"
              options={LANGUAGE_LEVEL}
              value={l.level}
              review={isReview(`languages.${i}.level`)}
              onChange={(v) => update({ level: v as LanguageItem['level'] })}
            />
          </div>
        )}
      />

      <ListEditor<CertificationItem>
        title="Certificaciones y cursos"
        items={form.certifications ?? []}
        onChange={setList('certifications')}
        addLabel="Agregar certificación"
        newItem={() => ({ name: '' })}
        render={(c, update) => (
          <div className="row g-2">
            <TextField
              className="col-md-6"
              label="Nombre"
              value={c.name}
              onChange={(v) => update({ name: v })}
            />
            <TextField
              className="col-md-4"
              label="Institución"
              value={c.issuer}
              onChange={(v) => update({ issuer: v })}
            />
            <TextField
              className="col-md-2"
              label="Año"
              type="number"
              value={c.year}
              onChange={(v) => update({ year: num(v) })}
            />
          </div>
        )}
      />

      <ListEditor<LinkItem>
        title="Links"
        items={form.links ?? []}
        onChange={setList('links')}
        addLabel="Agregar link"
        newItem={() => ({ type: 'linkedin', url: '' })}
        render={(l, update, i) => (
          <div className="row g-2">
            <SelectField
              className="col-md-4"
              label="Tipo"
              options={LINK_TYPE}
              value={l.type}
              onChange={(v) => update({ type: (v || 'other') as LinkItem['type'] })}
            />
            <TextField
              className="col-md-8"
              label="URL"
              type="url"
              value={l.url}
              placeholder="https://"
              review={isReview(`links.${i}.url`)}
              onChange={(v) => update({ url: v })}
            />
          </div>
        )}
      />

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
