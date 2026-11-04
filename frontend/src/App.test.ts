import { describe, expect, it } from 'vitest';
import { App } from './App';

describe('App', () => {
  it('se define correctamente el componente principal', () => {
    expect(App).toBeDefined();
  });
});