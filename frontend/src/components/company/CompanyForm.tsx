import React, { useState } from 'react';
import { CheckGroup, ListEditor, SelectField, Switch, TextField } from '../form/Fields';
import { CompanyLogo } from './CompanyLogo';
import {
  COMPANY_LINK_TYPE,
  COMPANY_MODALITY,
  COMPANY_SIZE,
  COMPANY_VISIBILITY,
  STEP_LABEL,
} from '../../profile/labels';
import { compact } from '../../profile/draft';
import { companyService, validateLogo } from '../../services/companyService';
import { errorMessage, validationMessages } from '../../services/api';
import type {
  CompanyLinkType,
  CompanyProfile,
  CompanySections,
  CompanyStep,
} from '../../types/company';
import type { Location, WorkModality } from '../../types/profile';

interface CompanyFormProps {
  profile: CompanyProfile;
  initialStep: CompanyStep;
  onProfileChange: (profile: CompanyProfile) => void;
  onDone: () => void;
}

const STEPS: CompanyStep[] = ['company', 'branding'];
const num = (v: string): number | undefined => (v.trim() === '' ? undefined : Number(v));
const toList = (v: string) =>
  v
    .split(',')
    .map((x) => x.trim())
    .filter(Boolean);

/** Alta/edición del perfil de empresa en dos pasos (contrato §2 y §6). */
export const CompanyForm: React.FC<CompanyFormProps> = ({
  profile,
  initialStep,
  onProfileChange,
  onDone,
}) => {
  const [step, setStep] = useState<CompanyStep>(initialStep);
  const [form, setForm] = useState<CompanySections>(() => ({
    display_name: profile.display_name ?? '',
    tagline: profile.tagline ?? '',
    description: profile.description ?? '',
    industry: profile.industry ?? '',
    size: profile.size,
    founded_year: profile.founded_year,
    location: { country: 'AR', province: '', city: '', ...profile.location },
    website: profile.website ?? '',
    links: profile.links ?? [],
    contact: { public: false, ...profile.contact },
    work_modalities: profile.work_modalities ?? [],
    hiring: profile.hiring ?? {},
    inclusive_hiring: profile.inclusive_hiring ?? {},
    visibility: profile.visibility ?? 'public',
  }));
  // Listas de texto libre como "a, b, c".
  const [benefits, setBenefits] = useState((profile.benefits ?? []).join(', '));
  const [values, setValues] = useState((profile.values ?? []).join(', '));
  const [areas, setAreas] = useState((profile.hiring?.areas ?? []).join(', '));
  const [agreements, setAgreements] = useState(
    (profile.hiring?.internship_agreements ?? []).join(', '),
  );
  const [saving, setSaving] = useState(false);
  const [logoBusy, setLogoBusy] = useState(false);
  const [error, setError] = useState<{ message: string; items: string[] } | null>(null);

  const set = (patch: Partial<CompanySections>) => setForm((f) => ({ ...f, ...patch }));
  const location = form.location as Location;
  const contact = form.contact!;
  const missing = (field: string) =>
    profile.completion.missing.some((m) => m.required && m.field.startsWith(field));

  const fail = (err: unknown) => {
    setError({ message: errorMessage(err), items: validationMessages(err) });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const save = async (sections: CompanySections, next: CompanyStep | null) => {
    setSaving(true);
    setError(null);
    try {
      onProfileChange(await companyService.update(compact(sections)));
      if (next) {
        setStep(next);
        window.scrollTo({ top: 0, behavior: 'smooth' });
      } else onDone();
    } catch (err) {
      fail(err);
    } finally {
      setSaving(false);
    }
  };

  const submitCompany = (e: React.FormEvent) => {
    e.preventDefault();
    const found: string[] = [];
    if (!form.display_name || form.display_name.trim().length < 2)
      found.push('Ingresá el nombre comercial.');
    if (!form.industry) found.push('Indicá el rubro.');
    if (!form.size) found.push('Elegí el tamaño de la empresa.');
    if (!location.country || !location.province || !location.city)
      found.push('Completá país, provincia y ciudad.');
    if (!form.description) found.push('Escribí una descripción.');
    if (!contact.email) found.push('Ingresá un email de contacto.');
    if (found.length) {
      setError({ message: 'Revisá estos datos:', items: found });
      return;
    }
    const { display_name, description, industry, size, founded_year, work_modalities, visibility } =
      form;
    save(
      {
        display_name,
        description,
        industry,
        size,
        founded_year,
        location,
        contact,
        work_modalities,
        visibility,
      },
      'branding',
    );
  };

  const submitBranding = (e: React.FormEvent) => {
    e.preventDefault();
    if (form.website && !/^https?:\/\//.test(form.website)) {
      setError({ message: 'La web tiene que empezar con https://', items: [] });
      return;
    }
    save(
      {
        tagline: form.tagline,
        website: form.website,
        links: (form.links ?? []).filter((l) => l.url),
        benefits: toList(benefits),
        values: toList(values),
        hiring: { ...form.hiring, areas: toList(areas), internship_agreements: toList(agreements) },
        inclusive_hiring: form.inclusive_hiring,
      },
      null,
    );
  };

  const uploadLogo = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    const invalid = validateLogo(file);
    if (invalid) {
      setError({ message: invalid, items: [] });
      return;
    }
    setLogoBusy(true);
    setError(null);
    try {
      onProfileChange(await companyService.uploadLogo(file));
    } catch (err) {
      fail(err);
    } finally {
      setLogoBusy(false);
    }
  };

  const removeLogo = async () => {
    setLogoBusy(true);
    try {
      await companyService.deleteLogo();
      onProfileChange((await companyService.getMine()) ?? profile);
    } catch (err) {
      fail(err);
    } finally {
      setLogoBusy(false);
    }
  };

  const saveButton = (label: string) => (
    <div className="d-flex justify-content-end">
      <button type="submit" className="btn btn-primary btn-pill" disabled={saving}>
        {saving && <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />}
        {label}
      </button>
    </div>
  );

  return (
    <div className="card card-elevated">
      <div className="card-body p-4 p-md-5">
        <ol
          className="nav nav-pills nav-fill gap-2 mb-4 list-unstyled"
          aria-label="Pasos del perfil"
        >
          {STEPS.map((s, i) => {
            const done = profile.completion.steps.find((x) => x.step === s)?.complete;
            return (
              <li key={s} className="nav-item">
                <button
                  type="button"
                  className={`nav-link w-100 ${s === step ? 'active' : ''}`}
                  aria-current={s === step ? 'step' : undefined}
                  onClick={() => setStep(s)}
                >
                  <span className="me-2">
                    {done ? (
                      <i className="bi bi-check-circle-fill" aria-label="completo" />
                    ) : (
                      `${i + 1}.`
                    )}
                  </span>
                  {STEP_LABEL[s]}
                </button>
              </li>
            );
          })}
        </ol>

        {error && (
          <div className="alert alert-danger small" role="alert">
            <strong>{error.message}</strong>
            {error.items.length > 0 && (
              <ul className="mb-0 mt-1">
                {error.items.map((i) => (
                  <li key={i}>{i}</li>
                ))}
              </ul>
            )}
          </div>
        )}

        {step === 'company' && (
          <form onSubmit={submitCompany} noValidate>
            <div className="bg-soft rounded-3 p-3 mb-4 small">
              <strong className="d-block mb-1">Datos legales (de tu cuenta)</strong>
              {profile.legal.legal_name} · CUIT {profile.legal.cuit} · {profile.legal.activity}
              <span className="d-block text-body-secondary mt-1">
                Se cargaron al registrarte y no se editan acá.
              </span>
            </div>
            <div className="row g-3 mb-4">
              <TextField
                className="col-md-6"
                label="Nombre comercial"
                required
                maxLength={120}
                value={form.display_name}
                review={missing('display_name')}
                onChange={(v) => set({ display_name: v })}
              />
              <TextField
                className="col-md-6"
                label="Rubro"
                required
                maxLength={80}
                value={form.industry}
                review={missing('industry')}
                onChange={(v) => set({ industry: v })}
              />
              <SelectField
                className="col-md-6"
                label="Tamaño"
                required
                options={COMPANY_SIZE}
                value={form.size}
                review={missing('size')}
                onChange={(v) => set({ size: (v || undefined) as CompanySections['size'] })}
              />
              <TextField
                className="col-md-6"
                label="Año de fundación"
                type="number"
                min={1800}
                max={2100}
                value={form.founded_year}
                onChange={(v) => set({ founded_year: num(v) })}
              />
              <TextField
                className="col-md-2"
                label="País"
                required
                maxLength={2}
                hint="Código de 2 letras"
                value={location.country}
                onChange={(v) => set({ location: { ...location, country: v.toUpperCase() } })}
              />
              <TextField
                className="col-md-5"
                label="Provincia"
                required
                value={location.province}
                review={missing('location')}
                onChange={(v) => set({ location: { ...location, province: v } })}
              />
              <TextField
                className="col-md-5"
                label="Ciudad"
                required
                hint="Sin calle ni número"
                value={location.city}
                review={missing('location')}
                onChange={(v) => set({ location: { ...location, city: v } })}
              />
              <TextField
                className="col-12"
                label="Descripción"
                required
                multiline
                maxLength={3000}
                value={form.description}
                review={missing('description')}
                onChange={(v) => set({ description: v })}
              />
            </div>

            <h3 className="h6 fw-bold mb-3">Contacto de RR. HH.</h3>
            <div className="row g-3 mb-4">
              <TextField
                className="col-md-4"
                label="Email"
                type="email"
                required
                value={contact.email}
                review={missing('contact')}
                onChange={(v) => set({ contact: { ...contact, email: v } })}
              />
              <TextField
                className="col-md-4"
                label="Teléfono"
                value={contact.phone}
                onChange={(v) => set({ contact: { ...contact, phone: v } })}
              />
              <TextField
                className="col-md-4"
                label="Nombre del contacto"
                value={contact.name}
                onChange={(v) => set({ contact: { ...contact, name: v } })}
              />
              <div className="col-12">
                <Switch
                  label="Mostrar el contacto a los estudiantes"
                  checked={contact.public}
                  onChange={(v) => set({ contact: { ...contact, public: v } })}
                />
              </div>
            </div>

            <div className="row g-3 mb-4">
              <CheckGroup<WorkModality>
                className="col-md-6"
                label="Modalidades de trabajo"
                hint="Informativo: la modalidad real va en cada búsqueda."
                options={COMPANY_MODALITY}
                values={form.work_modalities}
                onChange={(v) => set({ work_modalities: v })}
              />
              <SelectField
                className="col-md-6"
                label="Visibilidad del perfil"
                options={COMPANY_VISIBILITY}
                value={form.visibility}
                onChange={(v) => set({ visibility: (v || 'public') as 'public' | 'hidden' })}
              />
            </div>
            {saveButton('Guardar y seguir')}
          </form>
        )}

        {step === 'branding' && (
          <form onSubmit={submitBranding} noValidate>
            <section className="mb-4">
              <h3 className="h6 fw-bold mb-3">Logo</h3>
              <div className="d-flex align-items-center gap-3 flex-wrap">
                <CompanyLogo name={profile.name} url={profile.logo_url} size={88} />
                <div>
                  <label
                    htmlFor="company-logo"
                    className="btn btn-outline-primary btn-pill btn-sm mb-0"
                  >
                    {logoBusy ? (
                      <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />
                    ) : (
                      <i className="bi bi-image me-2" aria-hidden="true" />
                    )}
                    {profile.logo_url ? 'Cambiar logo' : 'Subir logo'}
                  </label>
                  <input
                    id="company-logo"
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    className="visually-hidden"
                    disabled={logoBusy}
                    onChange={uploadLogo}
                  />
                  {profile.logo_url && (
                    <button
                      type="button"
                      className="btn btn-link btn-sm text-danger"
                      disabled={logoBusy}
                      onClick={removeLogo}
                    >
                      Quitar
                    </button>
                  )}
                  <div className="form-text">
                    PNG, JPEG o WebP · máx. 1 MB · ideal cuadrado de 256 a 512 px.
                  </div>
                </div>
              </div>
            </section>

            <div className="row g-3 mb-4">
              <TextField
                className="col-md-6"
                label="Frase"
                maxLength={140}
                value={form.tagline}
                placeholder="Software a medida desde Buenos Aires"
                onChange={(v) => set({ tagline: v })}
              />
              <TextField
                className="col-md-6"
                label="Sitio web"
                type="url"
                value={form.website}
                placeholder="https://"
                onChange={(v) => set({ website: v })}
              />
            </div>

            <ListEditor<{ type: CompanyLinkType; url: string }>
              title="Redes"
              items={form.links ?? []}
              onChange={(links) => set({ links })}
              addLabel="Agregar red"
              newItem={() => ({ type: 'linkedin', url: '' })}
              render={(l, update) => (
                <div className="row g-2">
                  <SelectField
                    className="col-md-4"
                    label="Red"
                    options={COMPANY_LINK_TYPE}
                    value={l.type}
                    onChange={(v) => update({ type: (v || 'other') as CompanyLinkType })}
                  />
                  <TextField
                    className="col-md-8"
                    label="URL"
                    type="url"
                    value={l.url}
                    placeholder="https://"
                    onChange={(v) => update({ url: v })}
                  />
                </div>
              )}
            />

            <div className="row g-3 mb-4">
              <TextField
                className="col-md-6"
                label="Beneficios"
                hint="Separalos con comas (máx. 20)"
                value={benefits}
                placeholder="Prepaga, días de estudio"
                onChange={setBenefits}
              />
              <TextField
                className="col-md-6"
                label="Valores"
                hint="Separalos con comas (máx. 10)"
                value={values}
                placeholder="Aprendizaje continuo"
                onChange={setValues}
              />
            </div>

            <h3 className="h6 fw-bold mb-3">Qué perfiles contratan</h3>
            <div className="row g-3 mb-4">
              <TextField
                className="col-md-6"
                label="Áreas"
                hint="Separalas con comas (máx. 15)"
                value={areas}
                placeholder="Desarrollo backend, QA"
                onChange={setAreas}
              />
              <TextField
                className="col-md-6"
                label="Convenios de pasantías con universidades"
                hint="Separalos con comas"
                value={agreements}
                onChange={setAgreements}
              />
              <div className="col-md-6 d-grid gap-2">
                <Switch
                  label="Contratamos estudiantes"
                  checked={!!form.hiring?.hires_students}
                  onChange={(v) => set({ hiring: { ...form.hiring, hires_students: v } })}
                />
                <Switch
                  label="Tenemos programa de pasantías"
                  checked={!!form.hiring?.internship_program}
                  onChange={(v) => set({ hiring: { ...form.hiring, internship_program: v } })}
                />
              </div>
              <div className="col-md-6 d-grid gap-2">
                <Switch
                  label="Aceptamos CUD (certificado de discapacidad)"
                  checked={!!form.inclusive_hiring?.accepts_disability_certificate}
                  onChange={(v) =>
                    set({
                      inclusive_hiring: {
                        ...form.inclusive_hiring,
                        accepts_disability_certificate: v,
                      },
                    })
                  }
                />
                <Switch
                  label="Espacio de trabajo accesible"
                  checked={!!form.inclusive_hiring?.accessible_workplace}
                  onChange={(v) =>
                    set({ inclusive_hiring: { ...form.inclusive_hiring, accessible_workplace: v } })
                  }
                />
              </div>
            </div>
            {saveButton('Guardar y terminar')}
          </form>
        )}

        <div className="d-flex justify-content-between mt-4 pt-3 border-top">
          <button
            type="button"
            className="btn btn-link px-0"
            disabled={step === 'company'}
            onClick={() => setStep('company')}
          >
            <i className="bi bi-arrow-left me-1" aria-hidden="true" />
            Paso anterior
          </button>
          <button type="button" className="btn btn-link px-0" onClick={onDone}>
            Ir al panel
          </button>
        </div>
      </div>
    </div>
  );
};
