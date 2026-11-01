# ruff: noqa: E501
"""Generador determinístico de los workflows de n8n para Bolsa de Trabajo.

Genera en `n8n/workflows/` (sin secretos ni URLs hardcodeadas; todo vía `$env.*` y `mcp-tools`):
  - `WF-0R-router-nvidia.json`   (Sub-workflow: Router de modelos NVIDIA con fallback y cooldown)
  - `WF-0V-verificador.json`     (Sub-workflow: Verificador determinístico + LLM)
  - `WF-00-orquestador.json`     (Sub-workflow: Orquestador / Captain con reintento controlado)
  - `WF-01-procesar-cv.json`     (Webhook POST /webhook/cv-extract · CV Structurer)
  - `WF-06-recomendador.json`    (Webhook POST /webhook/recommendations · student & company)
"""

import json
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = ROOT / "services" / "ai-service" / "prompts"
OUT_DIR = ROOT / "n8n" / "workflows"

# IDs determinísticos de workflows para referencias entre Execute Workflow nodes y `n8n import:workflow`
WF_IDS = {
    "router": "BolsaWf0RRouterNvidia",
    "verifier": "BolsaWf0VVerificador0",
    "orchestrator": "BolsaWf00Orquestador0",
    "cv_extract": "BolsaWf01ExtractorCv0",
    "recommender": "BolsaWf06Recomendador",
}

# Credencial importada en bolsa-n8n-1 desde n8n-container (sin exponer la API key en el JSON)
NVIDIA_CRED = {"openAiApi": {"id": "PnIocs172tEX8ebB", "name": "OpenAI account"}}


def _nid(seed: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"bolsa.n8n.{seed}"))


def _read_prompt(name: str) -> str:
    text = (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].strip()
    return text.strip()


def _node(
    name: str,
    type_: str,
    version: float,
    pos: list[int],
    params: dict[str, Any] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "parameters": params or {},
        "id": _nid(name),
        "name": name,
        "type": type_,
        "typeVersion": version,
        "position": pos,
        **extra,
    }


def _code(name: str, js_code: str, pos: list[int]) -> dict[str, Any]:
    return _node(name, "n8n-nodes-base.code", 2, pos, {"jsCode": js_code})


def _note(name: str, content: str, pos: list[int], w: int = 500, h: int = 240) -> dict[str, Any]:
    return _node(
        name,
        "n8n-nodes-base.stickyNote",
        1,
        pos,
        {"content": content, "width": w, "height": h},
    )


def _conn(*edges: tuple[str, int, str]) -> dict[str, Any]:
    connections: dict[str, Any] = {}
    for src, out_idx, dst in edges:
        outs = connections.setdefault(src, {}).setdefault("main", [])
        while len(outs) <= out_idx:
            outs.append([])
        outs[out_idx].append({"node": dst, "type": "main", "index": 0})
    return connections


def _wf(
    wf_id: str, name: str, nodes: list[dict[str, Any]], connections: dict[str, Any]
) -> dict[str, Any]:
    return {
        "id": wf_id,
        "name": name,
        "nodes": nodes,
        "connections": connections,
        "active": False,
        "settings": {"executionOrder": "v1", "callerPolicy": "workflowsFromSameOwner"},
    }


# Helper JS común que se inyecta en los nodos Code para hablar con mcp-tools (JSON-RPC /mcp y /router/*)
MCP_HELPER_JS = r"""
const MCP_BASE = ($env.MCP_URL || 'http://mcp-tools:8000/mcp').replace(/\/mcp\/?$/, '');
const MCP_ENDPOINT = $env.MCP_URL || 'http://mcp-tools:8000/mcp';
const SVC_TOKEN = $env.SERVICE_TOKEN || '';

const callMcpTool = async (name, args = {}) => {
  const resp = await this.helpers.httpRequest({
    method: 'POST',
    url: MCP_ENDPOINT,
    json: true,
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json, text/event-stream',
      'X-Service-Token': SVC_TOKEN,
    },
    body: {
      jsonrpc: '2.0',
      id: Date.now(),
      method: 'tools/call',
      params: { name, arguments: args },
    },
  });
  const sc = resp?.result?.structuredContent;
  if (sc) return sc.result || sc;
  const txt = resp?.result?.content?.[0]?.text;
  if (txt) {
    try { return JSON.parse(txt); } catch (_) { return { ok: true, text: txt }; }
  }
  return resp;
};

const callRouterHttp = async (path, body) => {
  return await this.helpers.httpRequest({
    method: 'POST',
    url: `${MCP_BASE}/router/${path}`,
    json: true,
    timeout: 10000,
    headers: { 'X-Service-Token': SVC_TOKEN },
    body,
  });
};

const extractJsonObject = (rawText) => {
  const cleaned = String(rawText || '').replace(/<\/?think>/g, '').replace(/```(?:json)?/gi, '').trim();
  const match = cleaned.match(/\{[\s\S]*\}/);
  if (!match) throw new Error('El modelo no devolvió un bloque JSON');
  return JSON.parse(match[0]);
};
""".strip()


def build_wf_router() -> dict[str, Any]:
    """Sub-workflow WF-0R: Router de modelos NVIDIA con fallback, espera RPM y registro de estado."""
    reserve_js = (
        MCP_HELPER_JS
        + r"""

const item = $input.first().json;
const role = item.role || 'default';
const systemPrompt = item.system_prompt || '';
const userPrompt = item.user_prompt || '';
const maxAttempts = 4;

let tried = Array.isArray(item.tried) ? [...item.tried] : [];
let lastError = null;

for (let attempt = 0; attempt < maxAttempts; attempt++) {
  const res = await callRouterHttp('reserve', { role, tried });
  if (res.action === 'wait') {
    const waitMs = Math.min(Number(res.wait_ms) || 2000, 15000);
    await new Promise(r => setTimeout(r, waitMs));
    continue;
  }
  if (res.action !== 'call' || !res.model) {
    lastError = 'Sin modelos NVIDIA disponibles (en cooldown o límite RPM alcanzado)';
    break;
  }
  const chosenModel = res.model;
  tried.push(chosenModel);
  return [{
    json: {
      ok: true,
      action: 'call',
      role,
      model: chosenModel,
      nvidia_base_url: res.nvidia_base_url || 'https://integrate.api.nvidia.com/v1',
      temperature: res.temperature ?? 0.2,
      timeout_ms: (Number(res.timeout_seconds) || 60) * 1000,
      system_prompt: systemPrompt,
      user_prompt: userPrompt,
      tried,
    }
  }];
}

return [{
  json: {
    ok: false,
    action: 'exhausted',
    role,
    model: null,
    tried,
    error: lastError || 'Agotados los intentos de reserva de modelo NVIDIA',
  }
}];
"""
    )

    handle_response_js = (
        MCP_HELPER_JS
        + r"""

const prep = $('Reservar modelo NVIDIA').first().json;
if (!prep.ok || prep.action !== 'call') {
  return [{ json: prep }];
}

const llmItem = $input.first().json;
const content = llmItem?.choices?.[0]?.message?.content
  || llmItem?.message?.content
  || llmItem?.text
  || '';
const cleaned = String(content || '').replace(/<\/?think>/g, '').trim();

if (!cleaned || llmItem.error) {
  const errMsg = llmItem?.error?.message || JSON.stringify(llmItem?.error || 'Respuesta vacía del modelo');
  await callRouterHttp('failure', { model: prep.model, error: errMsg }).catch(() => null);
  return [{
    json: {
      ok: false,
      role: prep.role,
      model: prep.model,
      tried: prep.tried,
      error: errMsg,
    }
  }];
}

await callRouterHttp('success', { model: prep.model }).catch(() => null);
return [{
  json: {
    ok: true,
    role: prep.role,
    model: prep.model,
    tried: prep.tried,
    text: cleaned,
  }
}];
"""
    )

    nodes = [
        _node(
            "Entrada Subworkflow",
            "n8n-nodes-base.executeWorkflowTrigger",
            1.1,
            [0, 0],
            {"inputSource": "passthrough"},
        ),
        _code("Reservar modelo NVIDIA", reserve_js, [240, 0]),
        _node(
            "Llamar API NVIDIA (OpenAI Compatible)",
            "n8n-nodes-base.httpRequest",
            4.2,
            [500, 0],
            {
                "method": "POST",
                "url": "={{ $json.nvidia_base_url + '/chat/completions' }}",
                "authentication": "predefinedCredentialType",
                "nodeCredentialType": "openAiApi",
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": (
                    "={{ JSON.stringify({ model: $json.model, temperature: $json.temperature, "
                    "max_tokens: 4096, messages: ["
                    "{ role: 'system', content: $json.system_prompt }, "
                    "{ role: 'user', content: $json.user_prompt }"
                    "] }) }}"
                ),
                "options": {"timeout": 60000},
            },
            credentials=NVIDIA_CRED,
            onError="continueRegularOutput",
        ),
        _code("Registrar resultado en Router", handle_response_js, [760, 0]),
        _note(
            "Nota Router",
            "## WF-0R · Sub-workflow Router NVIDIA\n"
            "- Consulta a `mcp-tools` (`/router/reserve`) qué modelo corresponde según el rol (`default`, `cv`, `verifier`).\n"
            "- Llama a NVIDIA usando la credencial cifrada `OpenAI account` de n8n.\n"
            "- Registra éxito (`/router/success`) o fallo con cooldown exponencial (`/router/failure`).",
            [0, -260],
        ),
    ]
    return _wf(
        WF_IDS["router"],
        "WF-0R · Sub-workflow Router NVIDIA",
        nodes,
        _conn(
            ("Entrada Subworkflow", 0, "Reservar modelo NVIDIA"),
            ("Reservar modelo NVIDIA", 0, "Llamar API NVIDIA (OpenAI Compatible)"),
            ("Llamar API NVIDIA (OpenAI Compatible)", 0, "Registrar resultado en Router"),
        ),
    )


def build_wf_verifier() -> dict[str, Any]:
    """Sub-workflow WF-0V: Verificador determinístico (JSON Schema + Grounding + Score) + LLM."""
    verifier_prompt = json.dumps(_read_prompt("verifier"), ensure_ascii=False)

    det_check_js = (
        MCP_HELPER_JS
        + f"\nconst VERIFIER_SYSTEM_PROMPT = {verifier_prompt};\n"
        + r"""
const input = $input.first().json;
const schemaName = input.schema_name;
const candidateObj = input.candidate_json;
const sourceText = String(input.source_text || '');
const termsToCheck = Array.isArray(input.terms_to_check) ? input.terms_to_check : [];
const expectedScore = input.expected_score ?? null;
const reportedScore = input.reported_score ?? null;

const schemaRes = await callMcpTool('validate_json_schema', {
  schema_name: schemaName,
  payload_json: JSON.stringify(candidateObj),
});

const groundingRes = await callMcpTool('check_grounding', {
  terms: termsToCheck,
  source_text: sourceText,
  expected_score: expectedScore,
  reported_score: reportedScore,
});

const faltantes = [];
if (!schemaRes.valid) {
  for (const err of (schemaRes.errors || [])) {
    faltantes.push(`Schema (${schemaName}): ${err}`);
  }
}
if (!groundingRes.grounded) {
  if ((groundingRes.ungrounded_terms || []).length) {
    faltantes.push(`Competencias no respaldadas en el texto fuente: ${groundingRes.ungrounded_terms.join(', ')}`);
  }
  if (groundingRes.score_tampered) {
    faltantes.push(`El puntaje de reglas (${expectedScore}) fue alterado (${reportedScore})`);
  }
}

return [{
  json: {
    deterministic_passed: faltantes.length === 0,
    faltantes,
    schema_validation: schemaRes,
    grounding_check: groundingRes,
    role: 'verifier',
    system_prompt: VERIFIER_SYSTEM_PROMPT,
    user_prompt: JSON.stringify({
      schema_name: schemaName,
      schema_validation: schemaRes,
      grounding_check: groundingRes,
      candidate_output: candidateObj,
    }),
  }
}];
"""
    )

    eval_js = (
        MCP_HELPER_JS
        + r"""
const det = $('Validación determinística (MCP)').first().json;
if (!det.deterministic_passed) {
  return [{
    json: {
      cumple: false,
      faltantes: det.faltantes,
      instruccion: 'Corregí los errores de schema y eliminá cualquier término que no aparezca en el texto fuente.',
      verifier_model: 'deterministic-mcp',
      schema_validation: det.schema_validation,
      grounding_check: det.grounding_check,
    }
  }];
}

const llm = $input.first().json;
if (!llm.ok || !llm.text) {
  return [{
    json: {
      cumple: true,
      faltantes: [],
      instruccion: '',
      verifier_model: 'deterministic-mcp-fallback',
      schema_validation: det.schema_validation,
      grounding_check: det.grounding_check,
    }
  }];
}

try {
  const verdict = extractJsonObject(llm.text);
  const falt = Array.isArray(verdict.faltantes) ? verdict.faltantes.map(String) : [];
  return [{
    json: {
      cumple: verdict.cumple !== false && falt.length === 0,
      faltantes: falt,
      instruccion: String(verdict.instruccion || ''),
      verifier_model: llm.model || 'verifier',
      schema_validation: det.schema_validation,
      grounding_check: det.grounding_check,
    }
  }];
} catch (_) {
  return [{
    json: {
      cumple: true,
      faltantes: [],
      instruccion: '',
      verifier_model: llm.model || 'deterministic-mcp',
      schema_validation: det.schema_validation,
      grounding_check: det.grounding_check,
    }
  }];
}
"""
    )

    nodes = [
        _node(
            "Entrada Verificador",
            "n8n-nodes-base.executeWorkflowTrigger",
            1.1,
            [0, 0],
            {"inputSource": "passthrough"},
        ),
        _code("Validación determinística (MCP)", det_check_js, [260, 0]),
        _node(
            "Ejecutar Router NVIDIA (rol verifier)",
            "n8n-nodes-base.executeWorkflow",
            1.2,
            [520, 0],
            {
                "workflowId": {"__rl": True, "value": WF_IDS["router"], "mode": "id"},
                "mode": "once",
                "options": {"waitForSubWorkflow": True},
            },
        ),
        _code("Emitir veredicto final", eval_js, [780, 0]),
        _note(
            "Nota Verificador",
            "## WF-0V · Verificador\n"
            "1. Ejecuta `validate_json_schema` y `check_grounding` en `mcp-tools`.\n"
            "2. Verifica que ninguna competencia haya sido inventada y que el `score` por reglas esté intacto.\n"
            "3. Consulta al modelo `verifier` vía `WF-0R` y devuelve `{cumple, faltantes, instruccion}`.",
            [0, -260],
        ),
    ]
    return _wf(
        WF_IDS["verifier"],
        "WF-0V · Verificador de Agentes",
        nodes,
        _conn(
            ("Entrada Verificador", 0, "Validación determinística (MCP)"),
            ("Validación determinística (MCP)", 0, "Ejecutar Router NVIDIA (rol verifier)"),
            ("Ejecutar Router NVIDIA (rol verifier)", 0, "Emitir veredicto final"),
        ),
    )


def build_wf_orchestrator() -> dict[str, Any]:
    """Sub-workflow WF-00: Orquestador (Captain) que ejecuta al especialista, verifica y reintenta."""
    prompts_map = {
        "cv_extract": _read_prompt("cv_structurer"),
        "recommend_student": _read_prompt("training_advisor"),
        "recommend_company": _read_prompt("company_advisor"),
    }
    prompts_json = json.dumps(prompts_map, ensure_ascii=False)

    prep_js = (
        MCP_HELPER_JS
        + f"\nconst PROMPTS = {prompts_json};\n"
        + r"""
const req = $input.first().json;
const settings = await callMcpTool('get_agent_settings', {});
const task = req.task || 'cv_extract';

const roleMap = {
  cv_extract: 'cv',
  recommend_student: 'default',
  recommend_company: 'default',
};
const schemaMap = {
  cv_extract: 'cv_standard',
  recommend_student: 'student_recommendations',
  recommend_company: 'company_recommendations',
};

return [{
  json: {
    task,
    role: roleMap[task] || 'default',
    schema_name: schemaMap[task] || 'cv_standard',
    prompt_version: req.prompt_version || '1.0.0',
    system_prompt: PROMPTS[task] || PROMPTS.cv_extract,
    user_prompt: typeof req.payload === 'string' ? req.payload : JSON.stringify(req.payload),
    source_text: req.source_text || '',
    expected_score: req.expected_score ?? null,
    max_verify_retries: settings?.max_verify_retries ?? 1,
    settings,
  }
}];
"""
    )

    prep_verify_js = (
        MCP_HELPER_JS
        + r"""
const ctx = $('Preparar tarea y configuración').first().json;
const specialist = $input.first().json;

if (!specialist.ok || !specialist.text) {
  return [{
    json: {
      specialist_ok: false,
      error: specialist.error || 'El modelo especialista no devolvió respuesta',
      schema_name: ctx.schema_name,
      candidate_json: {},
      source_text: ctx.source_text,
      terms_to_check: [],
      expected_score: ctx.expected_score,
      reported_score: null,
      model: specialist.model || null,
    }
  }];
}

let parsed = {};
let parseError = null;
try {
  parsed = extractJsonObject(specialist.text);
} catch (err) {
  parseError = String(err.message || err);
}

let terms = [];
if (ctx.task === 'cv_extract' && Array.isArray(parsed.skills)) {
  terms = parsed.skills.map(s => String(s?.name || '')).filter(Boolean);
} else if (ctx.task === 'recommend_student' && Array.isArray(parsed.items)) {
  terms = parsed.items.map(i => String(i?.skill || '')).filter(Boolean);
}

if (ctx.task === 'cv_extract' && !parseError) {
  parsed.origin = 'AI';
  parsed.model = specialist.model || 'nvidia';
  parsed.prompt_version = ctx.prompt_version;
  parsed.generated_at = new Date().toISOString();
  parsed.disclaimer = 'Información extraída por IA como sugerencia. Revisá y confirmá antes de guardar en tu perfil.';
}

return [{
  json: {
    specialist_ok: !parseError,
    parse_error: parseError,
    schema_name: ctx.schema_name,
    candidate_json: parsed,
    source_text: ctx.source_text,
    terms_to_check: terms,
    expected_score: ctx.expected_score,
    reported_score: parsed.score ?? ctx.expected_score,
    model: specialist.model || 'nvidia',
  }
}];
"""
    )

    final_or_retry_js = (
        MCP_HELPER_JS
        + r"""
const ctx = $('Preparar tarea y configuración').first().json;
const cand = $('Preparar entrada del Verificador').first().json;
const verdict = $input.first().json;

if (cand.specialist_ok && verdict.cumple) {
  return [{
    json: {
      ok: true,
      needs_retry: false,
      status_code: 200,
      task: ctx.task,
      model: cand.model,
      prompt_version: ctx.prompt_version,
      verified: true,
      verifier_model: verdict.verifier_model,
      retries_used: 0,
      data: cand.candidate_json,
    }
  }];
}

return [{
  json: {
    ok: false,
    needs_retry: Number(ctx.max_verify_retries) > 0,
    task: ctx.task,
    role: ctx.role,
    schema_name: ctx.schema_name,
    prompt_version: ctx.prompt_version,
    source_text: ctx.source_text,
    expected_score: ctx.expected_score,
    system_prompt: ctx.system_prompt,
    user_prompt: `${ctx.user_prompt}\n\nCORRECCIÓN OBLIGATORIA DEL VERIFICADOR:\n- ${(verdict.faltantes || [cand.parse_error || 'JSON inválido']).join('\n- ')}\n${verdict.instruccion || ''}`,
    tried: [],
    previous_verdict: verdict,
  }
}];
"""
    )

    prep_verify_retry_js = (
        MCP_HELPER_JS
        + r"""
const ctx = $('Evaluar resultado o preparar reintento').first().json;
const specialist = $input.first().json;

let parsed = {};
let parseError = null;
try {
  parsed = extractJsonObject(specialist.text || '');
} catch (err) {
  parseError = String(err.message || err);
}

let terms = [];
if (ctx.task === 'cv_extract' && Array.isArray(parsed.skills)) {
  terms = parsed.skills.map(s => String(s?.name || '')).filter(Boolean);
} else if (ctx.task === 'recommend_student' && Array.isArray(parsed.items)) {
  terms = parsed.items.map(i => String(i?.skill || '')).filter(Boolean);
}

if (ctx.task === 'cv_extract' && !parseError) {
  parsed.origin = 'AI';
  parsed.model = specialist.model || 'nvidia';
  parsed.prompt_version = ctx.prompt_version;
  parsed.generated_at = new Date().toISOString();
  parsed.disclaimer = 'Información extraída por IA como sugerencia. Revisá y confirmá antes de guardar en tu perfil.';
}

return [{
  json: {
    specialist_ok: Boolean(specialist.ok && !parseError),
    parse_error: parseError,
    schema_name: ctx.schema_name,
    candidate_json: parsed,
    source_text: ctx.source_text,
    terms_to_check: terms,
    expected_score: ctx.expected_score,
    reported_score: parsed.score ?? ctx.expected_score,
    model: specialist.model || 'nvidia',
  }
}];
"""
    )

    after_retry_js = r"""
const ctx = $('Evaluar resultado o preparar reintento').first().json;
const cand = $('Preparar Verificador (Reintento)').first().json;
const verdict = $input.first().json;

if (cand.specialist_ok && verdict.cumple) {
  return [{
    json: {
      ok: true,
      status_code: 200,
      task: ctx.task,
      model: cand.model,
      prompt_version: ctx.prompt_version,
      verified: true,
      verifier_model: verdict.verifier_model,
      retries_used: 1,
      data: cand.candidate_json,
    }
  }];
}

return [{
  json: {
    ok: false,
    status_code: 422,
    task: ctx.task,
    retries_used: 1,
    previous_verdict: verdict,
  }
}];
""".strip()

    nodes = [
        _node(
            "Entrada Orquestador",
            "n8n-nodes-base.executeWorkflowTrigger",
            1.1,
            [0, 0],
            {"inputSource": "passthrough"},
        ),
        _code("Preparar tarea y configuración", prep_js, [240, 0]),
        _node(
            "Ejecutar Especialista (WF-0R)",
            "n8n-nodes-base.executeWorkflow",
            1.2,
            [500, 0],
            {
                "workflowId": {"__rl": True, "value": WF_IDS["router"], "mode": "id"},
                "mode": "once",
                "options": {"waitForSubWorkflow": True},
            },
        ),
        _code("Preparar entrada del Verificador", prep_verify_js, [760, 0]),
        _node(
            "Ejecutar Verificador (WF-0V)",
            "n8n-nodes-base.executeWorkflow",
            1.2,
            [1020, 0],
            {
                "workflowId": {"__rl": True, "value": WF_IDS["verifier"], "mode": "id"},
                "mode": "once",
                "options": {"waitForSubWorkflow": True},
            },
        ),
        _code("Evaluar resultado o preparar reintento", final_or_retry_js, [1280, 0]),
        _node(
            "¿Reintentar con feedback?",
            "n8n-nodes-base.if",
            2.2,
            [1540, 0],
            {
                "conditions": {
                    "options": {
                        "caseSensitive": True,
                        "leftValue": "",
                        "typeValidation": "loose",
                        "version": 2,
                    },
                    "conditions": [
                        {
                            "id": _nid("cond-needs-retry"),
                            "leftValue": "={{ $json.needs_retry }}",
                            "rightValue": "",
                            "operator": {
                                "type": "boolean",
                                "operation": "true",
                                "singleValue": True,
                            },
                        }
                    ],
                    "combinator": "and",
                },
                "options": {},
            },
        ),
        _node(
            "Reintentar Especialista (WF-0R)",
            "n8n-nodes-base.executeWorkflow",
            1.2,
            [1800, -120],
            {
                "workflowId": {"__rl": True, "value": WF_IDS["router"], "mode": "id"},
                "mode": "once",
                "options": {"waitForSubWorkflow": True},
            },
        ),
        _code("Preparar Verificador (Reintento)", prep_verify_retry_js, [2060, -120]),
        _node(
            "Ejecutar Verificador (Reintento)",
            "n8n-nodes-base.executeWorkflow",
            1.2,
            [2320, -120],
            {
                "workflowId": {"__rl": True, "value": WF_IDS["verifier"], "mode": "id"},
                "mode": "once",
                "options": {"waitForSubWorkflow": True},
            },
        ),
        _code("Resultado tras reintento", after_retry_js, [2580, -120]),
        _note(
            "Nota Orquestador",
            "## WF-00 · Orquestador (Captain)\n"
            "- Lee `get_agent_settings` desde `mcp-tools` al inicio de cada ejecución.\n"
            "- Ejecuta al especialista (`cv_extract`, `recommend_student`, `recommend_company`) vía `WF-0R`.\n"
            "- Pasa la salida por `WF-0V` (Verificador); si rechaza, reintenta 1 vez con el feedback antes de devolver 422/503.",
            [0, -260],
        ),
    ]
    return _wf(
        WF_IDS["orchestrator"],
        "WF-00 · Orquestador (Captain)",
        nodes,
        _conn(
            ("Entrada Orquestador", 0, "Preparar tarea y configuración"),
            ("Preparar tarea y configuración", 0, "Ejecutar Especialista (WF-0R)"),
            ("Ejecutar Especialista (WF-0R)", 0, "Preparar entrada del Verificador"),
            ("Preparar entrada del Verificador", 0, "Ejecutar Verificador (WF-0V)"),
            ("Ejecutar Verificador (WF-0V)", 0, "Evaluar resultado o preparar reintento"),
            ("Evaluar resultado o preparar reintento", 0, "¿Reintentar con feedback?"),
            ("¿Reintentar con feedback?", 0, "Reintentar Especialista (WF-0R)"),
            ("Reintentar Especialista (WF-0R)", 0, "Preparar Verificador (Reintento)"),
            ("Preparar Verificador (Reintento)", 0, "Ejecutar Verificador (Reintento)"),
            ("Ejecutar Verificador (Reintento)", 0, "Resultado tras reintento"),
        ),
    )


def build_wf_cv_extract() -> dict[str, Any]:
    """WF-01: Webhook POST /webhook/cv-extract para extraer y estructurar CVs (PDF/DOCX/DOC/MD)."""
    parse_cv_js = (
        MCP_HELPER_JS
        + r"""
const incoming = $input.first().json;
const headers = incoming.headers || {};
const body = incoming.body || incoming;

const givenToken = headers['x-webhook-token'] || headers['x-api-key'] || headers['x-service-token'] || '';
const validWebhook = $env.N8N_WEBHOOK_TOKEN && givenToken === $env.N8N_WEBHOOK_TOKEN;
const validService = $env.SERVICE_TOKEN && givenToken === $env.SERVICE_TOKEN;
if (!validWebhook && !validService) {
  throw new Error('No autorizado: falta o es inválido X-Webhook-Token / X-Service-Token');
}

let contentBase64 = body.content_base64 || body.base64 || '';
let filename = body.filename || body.nombre || 'cv.pdf';
let mimeType = body.mime_type || body.mime || '';

const binKeys = Object.keys($input.first().binary || {});
if (!contentBase64 && binKeys.length > 0) {
  const bKey = binKeys[0];
  const binMeta = $input.first().binary[bKey];
  const buf = await this.helpers.getBinaryDataBuffer(0, bKey);
  contentBase64 = buf.toString('base64');
  filename = binMeta.fileName || filename;
  mimeType = binMeta.mimeType || mimeType;
}

const parsed = await callMcpTool('parse_cv_file', {
  content_base64: contentBase64,
  filename,
  mime_type: mimeType,
});

if (!parsed.ok) {
  return [{
    json: {
      ok: false,
      status_code: 422,
      error: parsed.error || { code: 'CV_PARSE_ERROR', message: 'No se pudo leer el CV' },
    }
  }];
}

return [{
  json: {
    ok: true,
    task: 'cv_extract',
    prompt_version: '1.0.0',
    source_text: parsed.text,
    cv_meta: {
      filename: parsed.filename,
      format: parsed.format,
      chars: parsed.chars,
      truncated: parsed.truncated,
    },
    payload: {
      filename: parsed.filename,
      format: parsed.format,
      TEXTO_CV: parsed.text,
    },
  }
}];
"""
    )

    format_response_js = r"""
const parsedStep = $('Validar token y extraer texto CV (MCP)').first().json;
if (!parsedStep.ok) {
  return [{ json: parsedStep }];
}

const orq = $input.first().json;
if (!orq.ok) {
  return [{
    json: {
      ok: false,
      status_code: 503,
      error: {
        code: 'AI_EXTRACTION_FAILED',
        message: 'El agente no pudo estructurar el CV cumpliendo las reglas de verificación',
        details: orq.previous_verdict || {},
      },
    }
  }];
}

return [{
  json: {
    ok: true,
    cv_meta: parsedStep.cv_meta,
    cv_suggestions: orq.data,
    verification: {
      verified: orq.verified,
      verifier_model: orq.verifier_model,
    },
  }
}];
""".strip()

    nodes = [
        _node(
            "Webhook CV Extract",
            "n8n-nodes-base.webhook",
            2,
            [0, 0],
            {
                "httpMethod": "POST",
                "path": "cv-extract",
                "responseMode": "lastNode",
                "options": {},
            },
            webhookId=_nid("webhook-cv-extract"),
        ),
        _code("Validar token y extraer texto CV (MCP)", parse_cv_js, [260, 0]),
        _node(
            "Invocar Orquestador (WF-00)",
            "n8n-nodes-base.executeWorkflow",
            1.2,
            [520, 0],
            {
                "workflowId": {"__rl": True, "value": WF_IDS["orchestrator"], "mode": "id"},
                "mode": "once",
                "options": {"waitForSubWorkflow": True},
            },
        ),
        _code("Armar respuesta estandarizada (origin=AI)", format_response_js, [780, 0]),
        _note(
            "Nota WF-01",
            "## WF-01 · Procesar CV (`POST /webhook/cv-extract`)\n"
            "- Acepta PDF, DOCX, DOC y MD (base64 o multipart) protegido con `X-Webhook-Token` / `X-Service-Token`.\n"
            "- Extrae el texto con la herramienta MCP `parse_cv_file`.\n"
            "- Llama a `WF-00 Orquestador` (`task: cv_extract`) + `WF-0V Verificador`.\n"
            '- Devuelve `cv_suggestions` con `origin: "AI"` sin sobrescribir el perfil del estudiante.',
            [0, -260],
        ),
    ]
    return _wf(
        WF_IDS["cv_extract"],
        "WF-01 · Procesar CV (CV Structurer)",
        nodes,
        _conn(
            ("Webhook CV Extract", 0, "Validar token y extraer texto CV (MCP)"),
            ("Validar token y extraer texto CV (MCP)", 0, "Invocar Orquestador (WF-00)"),
            ("Invocar Orquestador (WF-00)", 0, "Armar respuesta estandarizada (origin=AI)"),
        ),
    )


def build_wf_recommender() -> dict[str, Any]:
    """WF-06: Webhook POST /webhook/recommendations (mode=student y mode=company)."""
    gather_context_js = (
        MCP_HELPER_JS
        + r"""
const incoming = $input.first().json;
const headers = incoming.headers || {};
const body = incoming.body || incoming;

const givenToken = headers['x-webhook-token'] || headers['x-api-key'] || headers['x-service-token'] || '';
const validWebhook = $env.N8N_WEBHOOK_TOKEN && givenToken === $env.N8N_WEBHOOK_TOKEN;
const validService = $env.SERVICE_TOKEN && givenToken === $env.SERVICE_TOKEN;
if (!validWebhook && !validService) {
  throw new Error('No autorizado: falta o es inválido X-Webhook-Token / X-Service-Token');
}

const settings = await callMcpTool('get_agent_settings', {});
const mode = (body.mode || (body.job_id && !body.profile_id ? 'company' : 'student')).toLowerCase();

if (mode === 'student') {
  const profileId = String(body.profile_id || 'stu-001');
  const profile = await callMcpTool('get_profile', { profile_id: profileId });
  if (!profile.ok) {
    return [{ json: { ok: false, status_code: 404, error: profile.error } }];
  }
  const jobsRes = await callMcpTool('list_active_jobs', {
    limit: settings?.recommendations?.max_jobs_per_student || 5,
  });
  const jobs = jobsRes.data || [];
  const minScore = Number(settings?.recommendations?.min_score || 0);

  const evaluations = [];
  for (const job of jobs) {
    const match = await callMcpTool('compute_match', { profile_id: profileId, job_id: job.id });
    if (Number(match.score) < minScore) continue;
    const gapsRes = await callMcpTool('missing_skills', { profile_id: profileId, job_id: job.id });
    const gaps = gapsRes.data || [];
    const gapSkills = gaps.map(g => g.skill);
    const coursesRes = gapSkills.length
      ? await callMcpTool('search_courses', { skills: gapSkills, limit: 5 })
      : { data: [] };
    evaluations.push({
      job,
      rule_based: {
        score: match.score,
        breakdown: match.breakdown,
        origin: 'RULES',
        engine_version: match.engine_version || '1.0.0',
      },
      missing_skills: gaps,
      available_courses: coursesRes.data || [],
    });
  }

  evaluations.sort((a, b) => b.rule_based.score - a.rule_based.score);
  const topEval = evaluations[0] || null;
  const sourceTerms = [
    ...(profile.skills || []).map(s => s.name),
    ...(topEval?.missing_skills || []).map(g => g.skill),
  ].join(', ');

  return [{
    json: {
      ok: true,
      mode: 'student',
      profile,
      evaluations,
      task: 'recommend_student',
      prompt_version: '1.0.0',
      source_text: sourceTerms,
      expected_score: topEval?.rule_based?.score ?? null,
      payload: {
        profile,
        job: topEval?.job || {},
        rule_based_match: topEval?.rule_based || {},
        missing_skills: topEval?.missing_skills || [],
        available_courses: topEval?.available_courses || [],
        max_items_per_job: settings?.recommendations?.max_items_per_job || 5,
      },
    }
  }];
}

// mode === 'company'
const jobId = String(body.job_id || 'job-001');
const job = await callMcpTool('get_job', { job_id: jobId });
if (!job.ok) {
  return [{ json: { ok: false, status_code: 404, error: job.error } }];
}

const candidatesRes = await callMcpTool('list_candidate_profiles', {
  skills: [],
  limit: settings?.recommendations?.max_profiles_per_job || 10,
});
const candidates = candidatesRes.data || [];

const ranked = [];
for (const cand of candidates) {
  const match = await callMcpTool('compute_match', { profile_id: cand.id, job_id: jobId });
  const gapsRes = await callMcpTool('missing_skills', { profile_id: cand.id, job_id: jobId });
  ranked.push({
    profile: cand,
    rule_based: {
      score: match.score,
      breakdown: match.breakdown,
      origin: 'RULES',
      engine_version: match.engine_version || '1.0.0',
    },
    missing_skills: gapsRes.data || [],
  });
}

// El ranking lo definen EXCLUSIVAMENTE las reglas (AGENTS.md §2.2)
ranked.sort((a, b) => b.rule_based.score - a.rule_based.score);
const topCandidate = ranked[0] || null;

return [{
  json: {
    ok: true,
    mode: 'company',
    job,
    ranked_candidates: ranked,
    task: 'recommend_company',
    prompt_version: '1.0.0',
    source_text: JSON.stringify({ job, candidate: topCandidate }),
    expected_score: topCandidate?.rule_based?.score ?? null,
    payload: {
      job,
      profile: topCandidate?.profile || {},
      rule_based_match: topCandidate?.rule_based || {},
      missing_skills: topCandidate?.missing_skills || [],
    },
  }
}];
"""
    )

    assemble_output_js = (
        MCP_HELPER_JS
        + r"""
const ctx = $('Obtener contexto y matching por reglas (MCP)').first().json;
if (!ctx.ok) {
  return [{ json: ctx }];
}

const orq = $input.first().json;
const aiBlock = {
  origin: 'AI',
  model: orq.model || 'nvidia',
  prompt_version: ctx.prompt_version || '1.0.0',
  generated_at: new Date().toISOString(),
  disclaimer: 'Recomendación orientativa generada por IA. El puntaje y el ranking provienen exclusivamente del motor de reglas.',
  verified: !!orq.verified,
};

if (ctx.mode === 'student') {
  const topEval = ctx.evaluations[0];
  const items = orq.ok && Array.isArray(orq.data?.items) ? orq.data.items : [];
  if (topEval && items.length > 0) {
    await callMcpTool('save_recommendation', {
      profile_id: ctx.profile.id,
      job_id: topEval.job.id,
      items,
      model: aiBlock.model,
      prompt_version: aiBlock.prompt_version,
      disclaimer: aiBlock.disclaimer,
    }).catch(() => null);
  }
  return [{
    json: {
      ok: true,
      mode: 'student',
      profile_id: ctx.profile.id,
      matches: ctx.evaluations.map((ev, idx) => ({
        job: ev.job,
        rule_based: ev.rule_based,
        missing_skills: ev.missing_skills,
        ai_recommendations: idx === 0 ? { ...aiBlock, items } : null,
      })),
    }
  }];
}

return [{
  json: {
    ok: true,
    mode: 'company',
    job_id: ctx.job.id,
    candidates: ctx.ranked_candidates.map((cand, idx) => ({
      profile: cand.profile,
      rule_based: cand.rule_based,
      missing_skills: cand.missing_skills,
      ai_recommendations: idx === 0 && orq.ok ? { ...aiBlock, ...orq.data } : null,
    })),
  }
}];
"""
    )

    nodes = [
        _node(
            "Webhook Recommendations",
            "n8n-nodes-base.webhook",
            2,
            [0, 0],
            {
                "httpMethod": "POST",
                "path": "recommendations",
                "responseMode": "lastNode",
                "options": {},
            },
            webhookId=_nid("webhook-recommendations"),
        ),
        _code("Obtener contexto y matching por reglas (MCP)", gather_context_js, [280, 0]),
        _node(
            "Invocar Orquestador (WF-00)",
            "n8n-nodes-base.executeWorkflow",
            1.2,
            [560, 0],
            {
                "workflowId": {"__rl": True, "value": WF_IDS["orchestrator"], "mode": "id"},
                "mode": "once",
                "options": {"waitForSubWorkflow": True},
            },
        ),
        _code("Separar bloques RULES vs AI y guardar", assemble_output_js, [840, 0]),
        _note(
            "Nota WF-06",
            "## WF-06 · Recomendador (`POST /webhook/recommendations`)\n"
            '- `mode=student` (`profile_id`): busca ofertas activas, calcula `compute_match` (`origin="RULES"`), '
            "`missing_skills` y cursos (`search_courses`), genera consejos con `Training Advisor` y persiste con `save_recommendation`.\n"
            "- `mode=company` (`job_id`): rankea candidatos **exclusivamente por reglas (`compute_match`)** y el LLM sólo redacta la justificación.",
            [0, -280],
            w=560,
            h=260,
        ),
    ]
    return _wf(
        WF_IDS["recommender"],
        "WF-06 · Recomendador (Postulantes y Empresas)",
        nodes,
        _conn(
            ("Webhook Recommendations", 0, "Obtener contexto y matching por reglas (MCP)"),
            ("Obtener contexto y matching por reglas (MCP)", 0, "Invocar Orquestador (WF-00)"),
            ("Invocar Orquestador (WF-00)", 0, "Separar bloques RULES vs AI y guardar"),
        ),
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    workflows = {
        "WF-0R-router-nvidia.json": build_wf_router(),
        "WF-0V-verificador.json": build_wf_verifier(),
        "WF-00-orquestador.json": build_wf_orchestrator(),
        "WF-01-procesar-cv.json": build_wf_cv_extract(),
        "WF-06-recomendador.json": build_wf_recommender(),
    }
    for filename, payload in workflows.items():
        target = OUT_DIR / filename
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Generado: {target.relative_to(ROOT)} ({len(payload['nodes'])} nodos)")


if __name__ == "__main__":
    main()
