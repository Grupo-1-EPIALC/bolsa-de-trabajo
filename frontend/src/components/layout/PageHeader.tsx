import React from 'react';

interface PageHeaderProps {
  title: string;
  subtitle: React.ReactNode;
  icon: string;
}

/** Franja magenta con el título de cada página interna. */
export const PageHeader: React.FC<PageHeaderProps> = ({ title, subtitle, icon }) => (
  <div className="page-header py-4">
    <div className="container d-flex align-items-center gap-3">
      <span className="icon-circle bg-white text-magenta d-none d-sm-inline-flex">
        <i className={`bi ${icon}`} aria-hidden="true" />
      </span>
      <div>
        <h1 className="h2 mb-1">{title}</h1>
        <p className="mb-0">{subtitle}</p>
      </div>
    </div>
  </div>
);
