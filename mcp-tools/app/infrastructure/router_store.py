"""Persistencia del estado del router de modelos NVIDIA y reloj del sistema."""

import copy
import datetime
import json
import time
from pathlib import Path

from app.domain.ports import JsonDict


class SystemClock:
    """Implementación real de `Clock` en UTC."""

    def now_ms(self) -> int:
        return int(time.time() * 1000)

    def today(self) -> str:
        return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")

    def iso_now(self) -> str:
        return (
            datetime.datetime.now(datetime.UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )


class FileRouterStateStore:
    """Guarda el estado del router en JSON de forma atómica; sin disco opera en memoria."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path
        self._memory: JsonDict = {"global": [], "models": {}}

    def load(self) -> JsonDict:
        if self._path is not None:
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    self._memory = raw
            except (OSError, ValueError):
                pass
        return copy.deepcopy(self._memory)

    def save(self, state: JsonDict) -> None:
        self._memory = copy.deepcopy(state)
        if self._path is None:
            return
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self._path)
        except OSError:
            pass
