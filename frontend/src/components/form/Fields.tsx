import React, { useId } from 'react';
import type { Options } from '../../profile/labels';

interface BaseProps {
  label: string;
  /** Resalta el campo: la IA no encontró el dato o falta un obligatorio. */
  review?: boolean;
  /** La IA no copió el dato del CV: lo sugirió con su contenido y hay que revisarlo. */
  suggested?: boolean;
  hint?: string;
  required?: boolean;
  className?: string;
}

const ReviewHint: React.FC<{ show?: boolean }> = ({ show }) =>
  show ? (
    <div className="form-text text-warning-emphasis">
      <i className="bi bi-pencil-square me-1" aria-hidden="true" />
      Completalo: no lo encontramos en tu CV.
    </div>
  ) : null;

const SuggestedHint: React.FC<{ show?: boolean }> = ({ show }) =>
  show ? (
    <div className="form-text text-warning-emphasis">
      <i className="bi bi-stars me-1" aria-hidden="true" />
      Sugerido por la IA con el contenido de tu CV: revisalo antes de guardar.
    </div>
  ) : null;

interface TextFieldProps extends BaseProps {
  value: string | number | undefined;
  onChange: (value: string) => void;
  type?: string;
  placeholder?: string;
  multiline?: boolean;
  maxLength?: number;
  min?: number;
  max?: number;
  autoComplete?: string;
}

export const TextField: React.FC<TextFieldProps> = ({
  label,
  review,
  suggested,
  hint,
  required,
  className,
  value,
  onChange,
  type = 'text',
  placeholder,
  multiline,
  maxLength,
  min,
  max,
  autoComplete,
}) => {
  const id = useId();
  const empty = value === '' || value === undefined;
  const highlight = review && empty;
  const showSuggested = Boolean(suggested) && !empty;
  const inputClass = `form-control ${highlight ? 'border-warning bg-warning-subtle' : ''} ${
    showSuggested ? 'border-warning' : ''
  }`;
  return (
    <div className={className}>
      <label htmlFor={id} className="form-label">
        {label}
        {required && <span className="text-danger ms-1">*</span>}
      </label>
      {multiline ? (
        <textarea
          id={id}
          className={inputClass}
          rows={4}
          value={value ?? ''}
          placeholder={placeholder}
          maxLength={maxLength}
          onChange={(e) => onChange(e.target.value)}
        />
      ) : (
        <input
          id={id}
          type={type}
          className={inputClass}
          value={value ?? ''}
          placeholder={placeholder}
          maxLength={maxLength}
          min={min}
          max={max}
          autoComplete={autoComplete}
          onChange={(e) => onChange(e.target.value)}
        />
      )}
      {hint && <div className="form-text">{hint}</div>}
      <ReviewHint show={highlight} />
      <SuggestedHint show={showSuggested} />
    </div>
  );
};

interface SelectFieldProps extends BaseProps {
  value: string | number | undefined;
  options: Options;
  onChange: (value: string) => void;
  placeholder?: string;
}

export const SelectField: React.FC<SelectFieldProps> = ({
  label,
  review,
  hint,
  required,
  className,
  value,
  options,
  onChange,
  placeholder = 'Elegí una opción',
}) => {
  const id = useId();
  const current = value === undefined || value === '' || value === 0 ? '' : String(value);
  const highlight = review && current === '';
  return (
    <div className={className}>
      <label htmlFor={id} className="form-label">
        {label}
        {required && <span className="text-danger ms-1">*</span>}
      </label>
      <select
        id={id}
        className={`form-select ${highlight ? 'border-warning bg-warning-subtle' : ''}`}
        value={current}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">{placeholder}</option>
        {options.map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
      {hint && <div className="form-text">{hint}</div>}
      <ReviewHint show={highlight} />
    </div>
  );
};

interface CheckGroupProps<T extends string> extends BaseProps {
  values: T[] | undefined;
  options: ReadonlyArray<readonly [T, string]>;
  onChange: (values: T[]) => void;
}

export function CheckGroup<T extends string>({
  label,
  required,
  hint,
  review,
  className,
  values = [],
  options,
  onChange,
}: CheckGroupProps<T>) {
  const id = useId();
  const toggle = (v: T) =>
    onChange(values.includes(v) ? values.filter((x) => x !== v) : [...values, v]);
  return (
    <fieldset className={className}>
      <legend className="form-label fs-6">
        {label}
        {required && <span className="text-danger ms-1">*</span>}
      </legend>
      <div
        className={`d-flex flex-wrap gap-2 ${review && values.length === 0 ? 'p-2 rounded border border-warning bg-warning-subtle' : ''}`}
      >
        {options.map(([v, l]) => (
          <div key={v}>
            <input
              type="checkbox"
              className="btn-check"
              id={`${id}-${v}`}
              checked={values.includes(v)}
              onChange={() => toggle(v)}
              autoComplete="off"
            />
            <label className="btn btn-sm btn-outline-primary rounded-pill" htmlFor={`${id}-${v}`}>
              {l}
            </label>
          </div>
        ))}
      </div>
      {hint && <div className="form-text">{hint}</div>}
    </fieldset>
  );
}

interface SwitchProps {
  label: React.ReactNode;
  checked: boolean;
  onChange: (checked: boolean) => void;
  hint?: string;
}

export const Switch: React.FC<SwitchProps> = ({ label, checked, onChange, hint }) => {
  const id = useId();
  return (
    <div className="form-check form-switch">
      <input
        id={id}
        className="form-check-input"
        type="checkbox"
        role="switch"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
      />
      <label className="form-check-label" htmlFor={id}>
        {label}
      </label>
      {hint && <div className="form-text">{hint}</div>}
    </div>
  );
};

/** Lista editable genérica: cada ítem en una tarjeta con botón para quitarlo. */
interface ListEditorProps<T> {
  title: string;
  items: T[];
  onChange: (items: T[]) => void;
  newItem: () => T;
  addLabel: string;
  render: (item: T, update: (patch: Partial<T>) => void, index: number) => React.ReactNode;
  badge?: (item: T) => React.ReactNode;
  required?: boolean;
  review?: boolean;
  emptyText?: string;
}

export function ListEditor<T>({
  title,
  items,
  onChange,
  newItem,
  addLabel,
  render,
  badge,
  required,
  review,
  emptyText = 'Todavía no agregaste ninguno.',
}: ListEditorProps<T>) {
  const update = (i: number) => (patch: Partial<T>) =>
    onChange(items.map((it, idx) => (idx === i ? { ...it, ...patch } : it)));
  const remove = (i: number) => onChange(items.filter((_, idx) => idx !== i));
  return (
    <section className="mb-4">
      <div className="d-flex justify-content-between align-items-center mb-2">
        <h3 className="h6 fw-bold mb-0">
          {title}
          {required && <span className="text-danger ms-1">*</span>}
        </h3>
        <button
          type="button"
          className="btn btn-sm btn-outline-primary rounded-pill"
          onClick={() => onChange([...items, newItem()])}
        >
          <i className="bi bi-plus-lg me-1" aria-hidden="true" />
          {addLabel}
        </button>
      </div>
      {items.length === 0 && (
        <p className={`small mb-0 ${review ? 'text-warning-emphasis' : 'text-body-secondary'}`}>
          {emptyText}
        </p>
      )}
      <div className="d-grid gap-2">
        {items.map((item, i) => (
          <div key={i} className="border rounded-3 p-3 bg-white position-relative">
            <div className="d-flex justify-content-between align-items-start gap-2 mb-2">
              <span>{badge?.(item)}</span>
              <button
                type="button"
                className="btn btn-sm btn-link text-danger p-0"
                onClick={() => remove(i)}
                aria-label={`Quitar ítem ${i + 1} de ${title}`}
              >
                <i className="bi bi-trash3 me-1" aria-hidden="true" />
                Quitar
              </button>
            </div>
            {render(item, update(i), i)}
          </div>
        ))}
      </div>
    </section>
  );
}
