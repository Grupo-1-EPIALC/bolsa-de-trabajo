#!/bin/sh
# =============================================================================
# Arranque de n8n (servicio `n8n-init` de docker-compose.yml).
# Corre antes de n8n en cada `docker compose up`:
#   1. Crea/actualiza la credencial "OpenAI account" (NVIDIA NIM, API compatible con
#      OpenAI) con NVIDIA_API_KEY de .env. El id es fijo porque lo usa WF-0R.
#   2. Crea/actualiza la credencial "SMTP Bolsa" desde SMTP_HOST/SMTP_PORT (Mailpit en
#      dev). La usan los mails de WF-02 a WF-05. Id fijo.
#   3. Importa los workflows de /workflows (n8n/workflows). Tienen ids fijos, así que
#      reimportar actualiza en lugar de duplicar (los datos persistentes de cada workflow,
#      como los notification_key de los mails ya enviados, se conservan).
#   4. Publica (activa) cada workflow para que sus webhooks respondan.
# Así una base de n8n nueva o vacía nunca queda sin workflows.
# =============================================================================
set -eu

WORKFLOWS_DIR=/workflows
CREDENTIAL_ID=PnIocs172tEX8ebB
CREDENTIAL_NAME="OpenAI account"
SMTP_CREDENTIAL_ID=BolsaSmtpMail0001
SMTP_CREDENTIAL_NAME="SMTP Bolsa"
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

echo "[n8n-init] 1/4 credencial NVIDIA NIM"
if [ -n "${NVIDIA_API_KEY:-}" ]; then
  CRED_FILE="$TMP_DIR/nvidia.json" node -e '
    const fs = require("fs");
    fs.writeFileSync(process.env.CRED_FILE, JSON.stringify([{
      id: process.argv[1],
      name: process.argv[2],
      type: "openAiApi",
      data: { apiKey: process.env.NVIDIA_API_KEY, url: process.env.NVIDIA_BASE_URL },
    }]));
  ' "$CREDENTIAL_ID" "$CREDENTIAL_NAME"
  n8n import:credentials --input="$TMP_DIR/nvidia.json"
else
  echo "[n8n-init] AVISO: NVIDIA_API_KEY vacío en .env; los agentes de IA no van a poder llamar al modelo."
  echo "[n8n-init]        Cargalo en .env (o creá la credencial '$CREDENTIAL_NAME' en la UI de n8n)."
fi

echo "[n8n-init] 2/4 credencial SMTP ($SMTP_CREDENTIAL_NAME)"
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
  echo "[n8n-init] AVISO: SMTP_HOST vacío en .env; WF-02 a WF-05 no van a poder mandar mails."
fi

echo "[n8n-init] 3/4 importando workflows de $WORKFLOWS_DIR"
n8n import:workflow --separate --input="$WORKFLOWS_DIR"

echo "[n8n-init] 4/4 publicando workflows"
for file in "$WORKFLOWS_DIR"/*.json; do
  id=$(node -e 'console.log(require(process.argv[1]).id)' "$file")
  if n8n publish:workflow --id="$id" >/dev/null 2>&1; then
    echo "[n8n-init]   publicado $id ($(basename "$file"))"
  else
    echo "[n8n-init]   AVISO: no se pudo publicar $id; revisalo en la UI de n8n."
  fi
done

echo "[n8n-init] listo"
