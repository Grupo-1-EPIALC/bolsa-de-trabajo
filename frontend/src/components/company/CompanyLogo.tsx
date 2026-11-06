import React from 'react';

interface CompanyLogoProps {
  name: string;
  url?: string;
  size?: number;
}

/** Logo de la empresa o sus iniciales si no subió uno (contrato §7). */
export const CompanyLogo: React.FC<CompanyLogoProps> = ({ name, url, size = 72 }) => {
  const style = { width: size, height: size };
  if (url) {
    return (
      <img
        src={url}
        alt={`Logo de ${name}`}
        className="rounded-3 border bg-white object-fit-contain flex-shrink-0"
        style={style}
      />
    );
  }
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join('');
  return (
    <span
      className="brand-mark flex-shrink-0"
      style={{ ...style, fontSize: size / 2.6 }}
      role="img"
      aria-label={`Iniciales de ${name}`}
    >
      {initials || '?'}
    </span>
  );
};
