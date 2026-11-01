import { describe, expect, it } from 'vitest';
import { APP_TITLE } from './App';

describe('App', () => {
  it('tiene título en español', () => {
    expect(APP_TITLE).toBe('Bolsa de Trabajo');
  });
});
