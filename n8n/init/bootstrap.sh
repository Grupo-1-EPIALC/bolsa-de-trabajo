#!/bin/sh
# =============================================================================
# Arranque de n8n (entrypoint del servicio `n8n` de docker-compose.yml).
# Corre en el mismo contenedor, antes de n8n, en cada arranque:
#   1. Crea/actualiza la credencial "OpenAI account" (NVIDIA NIM, API compatible con
#      OpenAI) con NVIDIA_API_KEY de .env. El id es fijo porque lo usa WF-0R. La URL es
#      el proxy de mcp-tools (LLM_BASE_URL), que corta a los AGENT_LLM_TIMEOUT_SECONDS
#      para que WF-0R pase al modelo siguiente (el timeout del nodo de n8n no corta).
#   2. Crea/actualiza la credencial "SMTP Bolsa" desde SMTP_HOST/SMTP_PORT (Mailpit en
#      dev). La usan los mails de WF-02 a WF-05. Id fijo.
#   3. Crea la tabla bolsa.notifications_sent en la base de n8n (avisos ya enviados por
#      WF-02 a WF-05, para no repetir mails) y la credencial "Postgres n8n (avisos)".
#   4. Importa los workflows de /workflows (n8n/workflows). Tienen ids fijos, así que
#      reimportar actualiza en lugar de duplicar.
#   5. Publica (activa) cada workflow para que sus webhooks respondan (`publish:workflow`,
#      n8n 2.x: los workflows usan nodos y versiones de 2.x y no corren en 1.x).
# Así una base de n8n nueva o vacía nunca queda sin workflows.
# =============================================================================
set -eu

WORKFLOWS_DIR=/workflows
CREDENTIAL_ID=PnIocs172tEX8ebB
CREDENTIAL_NAME="OpenAI account"
SMTP_CREDENTIAL_ID=BolsaSmtpMail0001
SMTP_CREDENTIAL_NAME="SMTP Bolsa"
PG_CREDENTIAL_ID=BolsaN8nPostgres1
PG_CREDENTIAL_NAME="Postgres n8n (avisos)"
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

echo "[n8n-arranque] 1/5 credencial NVIDIA NIM"
if [ -n "${NVIDIA_API_KEY:-}" ]; then
  CRED_FILE="$TMP_DIR/nvidia.json" node -e '
    const fs = require("fs");
    fs.writeFileSync(process.env.CRED_FILE, JSON.stringify([{
      id: process.argv[1],
      name: process.argv[2],
      type: "openAiApi",
      data: { apiKey: process.env.NVIDIA_API_KEY, url: process.env.LLM_BASE_URL || process.env.NVIDIA_BASE_URL },
    }]));
  ' "$CREDENTIAL_ID" "$CREDENTIAL_NAME"
  n8n import:credentials --input="$TMP_DIR/nvidia.json"
else
  echo "[n8n-arranque] AVISO: NVIDIA_API_KEY vacío en .env; los agentes de IA no van a poder llamar al modelo."
  echo "[n8n-arranque]        Cargalo en .env (o creá la credencial '$CREDENTIAL_NAME' en la UI de n8n)."
fi

echo "[n8n-arranque] 2/5 credencial SMTP ($SMTP_CREDENTIAL_NAME)"
if [ -n "${SMTP_HOST:-}" ]; then
  CRED_FILE="$TMP_DIR/smtp.json" node -e '
    const fs = require("fs");
    const secure = /^(1|true|yes)$/i.test(process.env.SMTP_SECURE || "");
    fs.writeFileSync(process.env.CRED_FILE, JSON.stringify([{
      id: process.argv[1],
      name: process.argv[2],
      type: "smtp",
      data: {
        user: process.env.SMTP_USER || "",
        password: process.env.SMTP_PASSWORD || "",
        host: process.env.SMTP_HOST,
        port: Number(process.env.SMTP_PORT || 25),
        secure,
        disableStartTls: !secure && !process.env.SMTP_USER,
      },
    }]));
  ' "$SMTP_CREDENTIAL_ID" "$SMTP_CREDENTIAL_NAME"
  n8n import:credentials --input="$TMP_DIR/smtp.json"
else
  echo "[n8n-arranque] AVISO: SMTP_HOST vacío en .env; WF-02 a WF-05 no van a poder mandar mails."
fi

echo "[n8n-arranque] 3/5 tabla de avisos enviados y credencial Postgres"
# pg viene con n8n: la tabla se crea una vez (IF NOT EXISTS) y n8n_svc es su dueño.
NODE_PATH=/usr/local/lib/node_modules/n8n/node_modules node -e '
  const { Client } = require("pg");
  const client = new Client({
    host: process.env.DB_POSTGRESDB_HOST,
    port: Number(process.env.DB_POSTGRESDB_PORT || 5432),
    database: process.env.DB_POSTGRESDB_DATABASE,
    user: process.env.DB_POSTGRESDB_USER,
    password: process.env.DB_POSTGRESDB_PASSWORD,
  });
  client.connect()
    .then(() => client.query(`
      CREATE SCHEMA IF NOT EXISTS bolsa;
      CREATE TABLE IF NOT EXISTS bolsa.notifications_sent (
        notification_key text PRIMARY KEY,
        workflow text NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now()
      );`))
    .then(() => client.end())
    .catch((err) => { console.error("[n8n-arranque] ERROR creando bolsa.notifications_sent:", err.message); process.exit(1); });
'
CRED_FILE="$TMP_DIR/postgres.json" node -e '
  const fs = require("fs");
  fs.writeFileSync(process.env.CRED_FILE, JSON.stringify([{
    id: process.argv[1],
    name: process.argv[2],
    type: "postgres",
    data: {
      host: process.env.DB_POSTGRESDB_HOST,
      port: Number(process.env.DB_POSTGRESDB_PORT || 5432),
      database: process.env.DB_POSTGRESDB_DATABASE,
      user: process.env.DB_POSTGRESDB_USER,
      password: process.env.DB_POSTGRESDB_PASSWORD,
      ssl: "disable",
      allowUnauthorizedCerts: false,
      maxConnections: 5,
      sshTunnel: false,
    },
  }]));
' "$PG_CREDENTIAL_ID" "$PG_CREDENTIAL_NAME"
n8n import:credentials --input="$TMP_DIR/postgres.json"

echo "[n8n-arranque] 4/5 importando workflows de $WORKFLOWS_DIR"
n8n import:workflow --separate --input="$WORKFLOWS_DIR"

echo "[n8n-arranque] 5/5 publicando workflows"
for file in "$WORKFLOWS_DIR"/*.json; do
  id=$(node -e 'console.log(require(process.argv[1]).id)' "$file")
  if n8n publish:workflow --id="$id" >/dev/null 2>&1; then
    echo "[n8n-arranque]   publicado $id ($(basename "$file"))"
  else
    echo "[n8n-arranque]   AVISO: no se pudo publicar $id; revisalo en la UI de n8n."
  fi
done

echo "[n8n-arranque] listo"
