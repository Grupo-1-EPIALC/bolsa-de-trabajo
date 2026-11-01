"""Validador de JSON Schema (`SchemaValidator`) basado en `jsonschema`."""

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

DEFAULT_SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "data" / "schemas"


class JsonSchemaValidator:
    def __init__(self, schemas_dir: Path = DEFAULT_SCHEMAS_DIR) -> None:
        self._validators: dict[str, Draft202012Validator] = {}
        if schemas_dir.is_dir():
            for file in sorted(schemas_dir.glob("*.schema.json")):
                name = file.name.removesuffix(".schema.json")
                schema_doc: dict[str, Any] = json.loads(file.read_text(encoding="utf-8"))
                self._validators[name] = Draft202012Validator(schema_doc)

    def available(self) -> list[str]:
        return sorted(self._validators.keys())

    def validate(self, schema_name: str, document: object) -> list[str]:
        validator = self._validators.get(schema_name)
        if validator is None:
            return [f"Schema desconocido: {schema_name}"]
        errors: list[str] = []
        for err in sorted(validator.iter_errors(document), key=lambda e: list(e.path)):
            path = ".".join(str(p) for p in err.path) or "$"
            errors.append(f"{path}: {err.message}")
        return errors
