import { describe, expect, it } from 'vitest';
import { latestRequest } from './latestRequest';

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((r) => (resolve = r));
  return { promise, resolve };
}

describe('latestRequest', () => {
  it('sólo la última llamada sigue vigente', () => {
    const latest = latestRequest();
    const first = latest.next();
    const second = latest.next();
    expect(first()).toBe(false);
    expect(second()).toBe(true);
  });

  it('una respuesta vieja que llega tarde no pisa a la nueva', async () => {
    const latest = latestRequest();
    let shown = '';
    const load = async (request: Promise<string>) => {
      const isCurrent = latest.next();
      const result = await request;
      if (isCurrent()) shown = result;
    };

    const slowFullList = deferred<string>();
    const fastSearch = deferred<string>();
    const a = load(slowFullList.promise); // carga inicial sin filtro
    const b = load(fastSearch.promise); // búsqueda

    fastSearch.resolve('filtrado');
    await b;
    slowFullList.resolve('todas');
    await a;

    expect(shown).toBe('filtrado');
  });
});
