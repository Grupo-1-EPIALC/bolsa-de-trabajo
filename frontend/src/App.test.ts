import { describe, expect, it } from 'vitest';
import { App } from './App';

describe('[UT-FE-01] Renderizado inicial de la aplicación', () => {
  it('se define correctamente el componente principal', () => {
    expect(App).toBeDefined();
  });
});
