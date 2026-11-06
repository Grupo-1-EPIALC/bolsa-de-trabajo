"""Conversión genérica dataclass ↔ dict JSON (sin dependencias externas).

La usan el repositorio (documento persistido), las vistas de la API y el seed. Se apoya en
las anotaciones de tipos de las dataclasses del dominio, así que agregar un campo nuevo no
exige tocar este módulo (OCP).
"""

import dataclasses
import types
import typing
from datetime import UTC, datetime
from enum import Enum
from functools import cache
from typing import Any, Union, cast

# --------------------------------------------------------------------- salida ---


def to_plain(value: Any) -> Any:
    """Dataclass/enum/tuple/datetime → tipos JSON. Los `None` se conservan."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: to_plain(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        current = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        return current.isoformat()
    if isinstance(value, list | tuple | set | frozenset):
        return [to_plain(item) for item in value]
    if isinstance(value, dict):
        return {str(k): to_plain(v) for k, v in value.items()}
    return value


def drop_none(value: Any) -> Any:
    """Quita claves con `None` (para respuestas compactas)."""
    if isinstance(value, dict):
        return {k: drop_none(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [drop_none(v) for v in value]
    return value


# -------------------------------------------------------------------- entrada ---


class DecodeError(ValueError):
    """El documento no respeta los tipos del dominio."""


@cache
def _hints(cls: type) -> dict[str, Any]:
    return typing.get_type_hints(cls)


def from_plain[T](cls: type[T], data: Any, path: str = "") -> T:
    """dict JSON → dataclass del dominio, validando enums y tipos básicos."""
    return cast(T, _decode(cls, data, path or cls.__name__))


def _decode(tp: Any, value: Any, path: str) -> Any:
    origin = typing.get_origin(tp)
    if tp is Any:
        return value
    if origin in (Union, types.UnionType):
        args = [a for a in typing.get_args(tp) if a is not type(None)]
        if value is None:
            return None
        return _decode(args[0], value, path)
    if origin is tuple:
        if value is None:
            return ()
        if not isinstance(value, list | tuple):
            raise DecodeError(f"{path}: se esperaba una lista")
        item_type, *_rest = typing.get_args(tp)
        return tuple(_decode(item_type, v, f"{path}[{i}]") for i, v in enumerate(value))
    if origin is dict:
        if value is None:
            return None
        if not isinstance(value, dict):
            raise DecodeError(f"{path}: se esperaba un objeto")
        return dict(value)
    if isinstance(tp, type) and dataclasses.is_dataclass(tp):
        if not isinstance(value, dict):
            raise DecodeError(f"{path}: se esperaba un objeto")
        hints = _hints(tp)
        kwargs = {}
        for f in dataclasses.fields(tp):
            if f.name in value:
                kwargs[f.name] = _decode(hints[f.name], value[f.name], f"{path}.{f.name}")
        try:
            return tp(**kwargs)
        except TypeError as exc:
            raise DecodeError(f"{path}: faltan campos obligatorios ({exc})") from exc
    if isinstance(tp, type) and issubclass(tp, Enum):
        try:
            return tp(value)
        except ValueError as exc:
            allowed = ", ".join(str(m.value) for m in tp)
            raise DecodeError(f"{path}: valor {value!r} inválido (permitidos: {allowed})") from exc
    if tp is datetime:
        if isinstance(value, datetime):
            parsed = value
        else:
            try:
                parsed = datetime.fromisoformat(str(value))
            except ValueError as exc:
                raise DecodeError(f"{path}: fecha inválida") from exc
        return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed
    if tp is bool:
        if not isinstance(value, bool):
            raise DecodeError(f"{path}: se esperaba true/false")
        return value
    if tp is int:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise DecodeError(f"{path}: se esperaba un número entero")
        return int(value)
    if tp is float:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise DecodeError(f"{path}: se esperaba un número")
        return float(value)
    if tp is str:
        if not isinstance(value, str):
            raise DecodeError(f"{path}: se esperaba texto")
        return value
    return value
