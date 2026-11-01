"""Router de modelos NVIDIA: elige el primer modelo disponible respetando el límite por minuto y
pone en pausa (cooldown) a los modelos que fallan. Portado de `agentes/mcp-tools/router_estado.py`.

El estado vive en un solo proceso (mcp-tools) para que las ejecuciones paralelas de n8n no se pisen.
Los métodos no tienen `await`: cada operación es atómica dentro del event loop.
"""

import re
from typing import Any

from app.domain.ports import Clock, RouterStateStore

MINUTE_MS = 60_000
_RATE_LIMIT = re.compile(r"429|rate.?limit|too many requests|quota|exceeded|credits", re.I)
_UNAVAILABLE = re.compile(r"404|410|not found|does not exist|deprecated|no longer", re.I)
_DOWN = re.compile(
    r"5\d\d|timeout|timed out|terminated|aborted|offline|ECONN|socket|overloaded|unavailable|"
    r"bad gateway",
    re.I,
)


class ModelRouter:
    def __init__(self, store: RouterStateStore, clock: Clock) -> None:
        self._store = store
        self._clock = clock
        state = store.load()
        state.setdefault("global", [])
        state.setdefault("models", {})
        self._state: dict[str, Any] = state

    def _model(self, name: str, now: int, today: str) -> dict[str, Any]:
        entry: dict[str, Any] = self._state["models"].setdefault(name, {})
        entry["minute"] = [t for t in entry.get("minute", []) if now - t < MINUTE_MS]
        if (entry.get("day") or {}).get("date") != today:
            entry["day"] = {"date": today, "count": 0}
        return entry

    def _prune_global(self, now: int) -> list[int]:
        window: list[int] = [t for t in self._state["global"] if now - t < MINUTE_MS]
        self._state["global"] = window
        return window

    def reserve(self, order: list[str], tried: list[str], rpm_limit: int) -> dict[str, Any]:
        """Elige modelo y registra el uso en el mismo paso.

        → {"action": "call", "model"} | {"action": "wait", "wait_ms", "reason"} |
          {"action": "none", "wait_ms"}
        """
        now, today = self._clock.now_ms(), self._clock.today()
        window = self._prune_global(now)
        if len(window) >= rpm_limit:
            return {
                "action": "wait",
                "wait_ms": window[0] + MINUTE_MS - now,
                "reason": "global_rpm",
            }
        next_free: int | None = None
        for name in order:
            if name in tried:
                continue
            entry = self._model(name, now, today)
            cooldown = int(entry.get("cooldown_until") or 0)
            if cooldown > now:
                next_free = cooldown if next_free is None else min(next_free, cooldown)
                continue
            entry["minute"].append(now)
            entry["day"]["count"] += 1
            entry["last_used"] = self._clock.iso_now()
            window.append(now)
            self._store.save(self._state)
            return {"action": "call", "model": name}
        return {"action": "none", "wait_ms": next_free - now if next_free else None}

    def report_failure(self, model: str, error: str) -> dict[str, Any]:
        """Clasifica el error y pausa al modelo según el tipo. → {"kind", "cooldown_ms"}"""
        entry: dict[str, Any] = self._state["models"].setdefault(model, {})
        message = (error or "respuesta vacía del modelo")[:500]
        kind, pause = "other", 0
        if _RATE_LIMIT.search(message):
            kind = "rate_limit"
            entry["strikes"] = entry.get("strikes", 0) + 1
            pause = min(MINUTE_MS * 2 ** (entry["strikes"] - 1), 15 * MINUTE_MS)
        elif _UNAVAILABLE.search(message):
            kind, pause = "unavailable", 24 * 60 * MINUTE_MS
        elif _DOWN.search(message):
            kind = "down"
            entry["strikes"] = entry.get("strikes", 0) + 1
            pause = min(2 * MINUTE_MS * 2 ** (entry["strikes"] - 1), 30 * MINUTE_MS)
        if pause:
            entry["cooldown_until"] = self._clock.now_ms() + pause
        entry["last_error"] = {"at": self._clock.iso_now(), "kind": kind, "error": message[:200]}
        self._store.save(self._state)
        return {"kind": kind, "cooldown_ms": pause}

    def report_success(self, model: str) -> dict[str, Any]:
        entry: dict[str, Any] = self._state["models"].setdefault(model, {})
        if entry.get("strikes"):
            entry["strikes"] = 0
            self._store.save(self._state)
        return {"ok": True}

    def status(self) -> dict[str, Any]:
        now, today = self._clock.now_ms(), self._clock.today()
        self._prune_global(now)
        for name in list(self._state["models"]):
            self._model(name, now, today)
        return self._state
