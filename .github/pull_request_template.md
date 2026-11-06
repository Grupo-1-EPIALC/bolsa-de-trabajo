## Historia de usuario
HU-XX — <título>

## Qué cambia
-

## Cómo probar
```bash
sh infra/scripts/create-volumes.sh   # sólo la primera vez
docker compose up -d --build
```
1.

## Checklist DoD
- [ ] Rama `<tipo>/<servicio>/vX.Y.Z-<desc>` y versión actualizada en `pyproject.toml` / `package.json`
- [ ] Tests unitarios agregados/actualizados y en verde (cobertura ≥ 70 % en `domain/` y `application/`)
- [ ] Lint / format / tipos sin errores
- [ ] Contrato actualizado en `contracts/` (si cambió un endpoint o schema)
- [ ] `.env.example` actualizado (si hay variables nuevas) · sin secretos en el código
- [ ] Resultados por reglas con `origin: "RULES"` / de IA con `origin: "AI"` (si aplica)

## Prompts usados (PROMPTS.md)
- P-NNN
