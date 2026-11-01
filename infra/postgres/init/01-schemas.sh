#!/bin/sh
# -----------------------------------------------------------------------------
# Crea un rol y un schema por servicio. Cada rol sólo puede usar su schema:
# "un servicio no accede a la base de datos de otro" (AGENTS.md §2.1.4).
# Se ejecuta UNA vez, al crear el volumen pg_data. Para re-ejecutar:
#   docker compose down -v && docker compose up -d
# -----------------------------------------------------------------------------
set -eu

create_service_schema() {
  role="$1"; schema="$2"; password="$3"
  echo "-> rol ${role} / schema ${schema}"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
       -v role="$role" -v schema="$schema" -v pwd="$password" <<'SQL'
CREATE ROLE :"role" LOGIN PASSWORD :'pwd';
CREATE SCHEMA :"schema" AUTHORIZATION :"role";
ALTER ROLE :"role" SET search_path = :"schema";
GRANT CONNECT ON DATABASE :"DBNAME" TO :"role";
SQL
}

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
REVOKE ALL ON DATABASE :"DBNAME" FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
SQL

create_service_schema auth_svc     auth     "$AUTH_DB_PASSWORD"
create_service_schema profile_svc  profile  "$PROFILE_DB_PASSWORD"
create_service_schema jobs_svc     jobs     "$JOBS_DB_PASSWORD"
create_service_schema matching_svc matching "$MATCHING_DB_PASSWORD"
create_service_schema ai_svc       ai       "$AI_DB_PASSWORD"

# n8n es una herramienta externa que gestiona su propio esquema (corre
# CREATE SCHEMA al iniciar): se le da una base separada de la que es dueño.
echo "-> rol n8n_svc / base n8n"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
     -v pwd="$N8N_DB_PASSWORD" <<'SQL'
CREATE ROLE n8n_svc LOGIN PASSWORD :'pwd';
CREATE DATABASE n8n OWNER n8n_svc;
REVOKE ALL ON DATABASE n8n FROM PUBLIC;
SQL
