#!/bin/sh
# Crea (una sola vez) los volúmenes externos con los datos persistentes del stack.
# Compose no los crea ni los borra: sobreviven a `docker compose down -v`.
# Si ya existen, no hace nada. Uso: sh infra/scripts/create-volumes.sh
set -eu
PROJECT=${COMPOSE_PROJECT_NAME:-bolsa}
for name in pg_data n8n_data cv_storage; do
  volume="${PROJECT}_${name}"
  if docker volume inspect "$volume" >/dev/null 2>&1; then
    echo "ya existe: $volume"
  else
    docker volume create "$volume" >/dev/null
    echo "creado:    $volume"
  fi
done
