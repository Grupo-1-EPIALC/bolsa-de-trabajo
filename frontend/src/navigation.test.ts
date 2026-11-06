import { describe, expect, it } from 'vitest';
import { resolveView } from './navigation';

describe('resolveView', () => {
  it('sin sesión muestra la portada en lugar del área privada', () => {
    expect(resolveView('app', false)).toBe('home');
  });

  it('sin sesión permite la portada y el acceso', () => {
    expect(resolveView('home', false)).toBe('home');
    expect(resolveView('auth', false)).toBe('auth');
  });

  it('con sesión lleva siempre al área del usuario', () => {
    expect(resolveView('home', true)).toBe('app');
    expect(resolveView('auth', true)).toBe('app');
    expect(resolveView('app', true)).toBe('app');
  });
});
