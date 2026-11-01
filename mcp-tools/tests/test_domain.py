"""Tests unitarios de la capa de dominio (`settings`, `grounding`, `router`)."""

import pytest

from app.domain.errors import InvalidInputError
from app.domain.grounding import find_ungrounded, normalize
from app.domain.ports import JsonDict
from app.domain.router import MINUTE_MS, ModelRouter
from app.domain.settings import AgentSettings, CvSettings, RecommendationSettings


class FakeClock:
    def __init__(self, now_ms: int = 1_000_000, today: str = "2026-10-31") -> None:
        self.current_ms = now_ms
        self.current_day = today

    def now_ms(self) -> int:
        return self.current_ms

    def today(self) -> str:
        return self.current_day

    def iso_now(self) -> str:
        return f"{self.current_day}T12:00:00Z"


class InMemoryRouterStore:
    def __init__(self) -> None:
        self.state: JsonDict = {}

    def load(self) -> JsonDict:
        return dict(self.state)

    def save(self, state: JsonDict) -> None:
        self.state = dict(state)


def _valid_settings() -> AgentSettings:
    return AgentSettings(
        nvidia_base_url="https://integrate.api.nvidia.com/v1",
        models={
            "default": ("model-a", "model-b"),
            "cv": ("model-b",),
            "verifier": ("model-a",),
        },
        rpm_limit=40,
        llm_timeout_seconds=60,
        temperature=0.2,
        max_verify_retries=1,
        recommendations=RecommendationSettings(
            max_jobs_per_student=5,
            max_profiles_per_job=10,
            max_items_per_job=5,
            min_score=0.0,
        ),
        cv=CvSettings(
            max_size_mb=5.0,
            allowed_extensions=("pdf", "docx", "doc", "md"),
            max_text_chars=40000,
        ),
    )


def test_agent_settings_valid_and_to_dict() -> None:
    cfg = _valid_settings()
    assert cfg.cv.max_size_bytes == 5 * 1024 * 1024
    assert cfg.models_for("cv") == ("model-b",)
    as_dict = cfg.to_dict()
    assert as_dict["rpm_limit"] == 40
    assert as_dict["models"] == {
        "default": ["model-a", "model-b"],
        "cv": ["model-b"],
        "verifier": ["model-a"],
    }


def test_agent_settings_validation_errors() -> None:
    base = _valid_settings()
    with pytest.raises(InvalidInputError, match="Faltan modelos"):
        AgentSettings(
            nvidia_base_url=base.nvidia_base_url,
            models={"default": ("m1",), "cv": (), "verifier": ("m1",)},
            rpm_limit=40,
            llm_timeout_seconds=60,
            temperature=0.2,
            max_verify_retries=1,
            recommendations=base.recommendations,
            cv=base.cv,
        )
    with pytest.raises(InvalidInputError, match="mayores que 0"):
        AgentSettings(
            nvidia_base_url=base.nvidia_base_url,
            models=base.models,
            rpm_limit=0,
            llm_timeout_seconds=60,
            temperature=0.2,
            max_verify_retries=1,
            recommendations=base.recommendations,
            cv=base.cv,
        )
    with pytest.raises(InvalidInputError, match="max_verify_retries"):
        AgentSettings(
            nvidia_base_url=base.nvidia_base_url,
            models=base.models,
            rpm_limit=40,
            llm_timeout_seconds=60,
            temperature=0.2,
            max_verify_retries=-1,
            recommendations=base.recommendations,
            cv=base.cv,
        )
    with pytest.raises(InvalidInputError, match="temperature"):
        AgentSettings(
            nvidia_base_url=base.nvidia_base_url,
            models=base.models,
            rpm_limit=40,
            llm_timeout_seconds=60,
            temperature=2.5,
            max_verify_retries=1,
            recommendations=base.recommendations,
            cv=base.cv,
        )
    with pytest.raises(InvalidInputError, match="Rol de modelo desconocido"):
        base.models_for("unknown")


def test_grounding_normalize_and_find_ungrounded() -> None:
    source = "Experiencia en Python 3.12, Node.js, C++, .NET y diseño de APIs REST con FastAPI."
    assert normalize("  Diseño   de ÁPIs ") == "diseno de apis"
    missing = find_ungrounded(
        ["Python", "node.js", "C++", ".NET", "Kubernetes", "kubernetes", "FastAPI"],
        source,
    )
    assert missing == ["Kubernetes"]


def test_model_router_reserve_cooldown_and_rpm() -> None:
    clock = FakeClock()
    store = InMemoryRouterStore()
    router = ModelRouter(store=store, clock=clock)

    first = router.reserve(["m1", "m2"], tried=[], rpm_limit=2)
    assert first == {"action": "call", "model": "m1"}

    second = router.reserve(["m1", "m2"], tried=["m1"], rpm_limit=2)
    assert second == {"action": "call", "model": "m2"}

    # Tercer pedido dentro del mismo minuto alcanza rpm_limit=2
    third = router.reserve(["m1", "m2"], tried=[], rpm_limit=2)
    assert third["action"] == "wait"
    assert third["reason"] == "global_rpm"

    # Avanza el reloj 1 minuto: se libera la ventana global
    clock.current_ms += MINUTE_MS + 1
    fail = router.report_failure("m1", "HTTP 429 Too Many Requests: rate limit exceeded")
    assert fail == {"kind": "rate_limit", "cooldown_ms": MINUTE_MS}

    # m1 está en cooldown -> salta a m2
    fourth = router.reserve(["m1", "m2"], tried=[], rpm_limit=5)
    assert fourth == {"action": "call", "model": "m2"}

    # Si m2 ya fue intentado y m1 está en cooldown -> devuelve none con wait_ms
    none_res = router.reserve(["m1", "m2"], tried=["m2"], rpm_limit=5)
    assert none_res["action"] == "none"
    assert none_res["wait_ms"] == MINUTE_MS

    # Fallos 404 y 503
    unavail = router.report_failure("m2", "404 model does not exist")
    assert unavail["kind"] == "unavailable"
    down = router.report_failure("m3", "503 Service Unavailable")
    assert down["kind"] == "down"

    # report_success limpia strikes
    ok = router.report_success("m1")
    assert ok == {"ok": True}
    status = router.status()
    assert status["models"]["m1"]["strikes"] == 0

