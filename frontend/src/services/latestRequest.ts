/**
 * Descarta respuestas viejas cuando un listado se vuelve a pedir antes de que llegue la anterior
 * (cambiar de filtro, de pestaña o de página). Cada llamada a `next()` invalida las anteriores y
 * devuelve `isCurrent`: después del `await`, sólo se guarda el resultado si sigue siendo la última.
 *
 *   const latest = useRef(latestRequest()).current;
 *   const isCurrent = latest.next();
 *   const result = await service.list(filtros);
 *   if (isCurrent()) setData(result);
 */
export function latestRequest() {
  let current = 0;
  return {
    next(): () => boolean {
      const id = ++current;
      return () => id === current;
    },
  };
}
