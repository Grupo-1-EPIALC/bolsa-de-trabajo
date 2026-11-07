import React from 'react';

interface PaginationProps {
  page: number;
  pages: number;
  onPage: (page: number) => void;
  label: string;
}

/** Controles de página (1-based) con "Anterior / Siguiente". No se muestra con una sola página. */
export const Pagination: React.FC<PaginationProps> = ({ page, pages, onPage, label }) => {
  if (pages <= 1) return null;
  return (
    <nav aria-label={label} className="d-flex justify-content-center align-items-center gap-3">
      <button
        type="button"
        className="btn btn-sm btn-outline-primary btn-pill"
        onClick={() => onPage(page - 1)}
        disabled={page <= 1}
      >
        <i className="bi bi-chevron-left me-1" aria-hidden="true" />
        Anterior
      </button>
      <span className="small" aria-live="polite">
        Página {page} de {pages}
      </span>
      <button
        type="button"
        className="btn btn-sm btn-outline-primary btn-pill"
        onClick={() => onPage(page + 1)}
        disabled={page >= pages}
      >
        Siguiente
        <i className="bi bi-chevron-right ms-1" aria-hidden="true" />
      </button>
    </nav>
  );
};
