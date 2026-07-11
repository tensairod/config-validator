"""Valida e coerciona os valores brutos vindos do Loader contra um Schema.

Este é o ponto de encontro entre o Domain (Field, Schema, CrossValidator,
SecretValue — puros, sem I/O) e o Pydantic v2 (ADR-001: delegamos a
coerção de tipos a ele, não reimplementamos parsing).

Fluxo de `validate()`:
1. Constrói um modelo Pydantic dinâmico a partir do Schema.
2. Pré-processa valores de campos LIST (string "a,b,c" -> lista).
3. Valida com Pydantic. Se houver erros, formata cada um com
   `error_formatter` e levanta UM ConfigValidationError agregando todos
   (ADR-004) — nunca na primeira violação.
4. Se a validação de campo passou integralmente, roda as validações
   cruzadas do Schema sobre os valores já tipados. Violações aqui também
   são agregadas antes de levantar o erro.
5. Envolve em SecretValue todo valor final de campo marcado como
   `secret=True` — fechando o débito técnico descrito em
   docs/architecture.md ("SecretValue no runtime, não só no default").
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import AnyUrl, ConfigDict, create_model
from pydantic import ValidationError as PydanticValidationError

from config_validator.application.error_formatter import format_pydantic_errors
from config_validator.application.errors import ConfigValidationError
from config_validator.domain.field import Field, FieldKind
from config_validator.domain.schema import Schema
from config_validator.domain.secret import SecretValue

_SIMPLE_KIND_TO_TYPE: dict[FieldKind, Any] = {
    FieldKind.STR: str,
    FieldKind.INT: int,
    FieldKind.BOOL: bool,
    FieldKind.FLOAT: float,
    FieldKind.URL: AnyUrl,
    FieldKind.PATH: Path,
}


class Validator:
    """Valida um dict de valores brutos (str) contra um Schema, devolvendo
    um dict plano de valores já tipados e coeridos.

    Note que o resultado é um dict PLANO — mesmo para campos com namespace
    (ex: 'db__host'), a chave continua sendo a string 'db__host'. Montar o
    objeto de configuração final com atributos aninhados (`config.db.host`)
    é responsabilidade de um componente separado (ConfigBuilder, próxima
    issue), que consome o resultado deste Validator.
    """

    def validate(self, schema: Schema, raw_values: Mapping[str, str]) -> dict[str, Any]:
        model_cls = self._build_model(schema)
        prepared_values = self._prepare_list_fields(schema, raw_values)

        try:
            instance = model_cls(**prepared_values)
        except PydanticValidationError as exc:
            messages = format_pydantic_errors(exc.errors(), schema)
            raise ConfigValidationError(messages) from exc

        resolved: dict[str, Any] = instance.model_dump()

        cross_validation_errors = schema.run_cross_validators(resolved)
        if cross_validation_errors:
            raise ConfigValidationError(cross_validation_errors)

        return self._wrap_secrets(schema, resolved)

    def _build_model(self, schema: Schema) -> Any:
        field_definitions: dict[str, Any] = {}
        for field in schema.fields:
            python_type = self._python_type_for(field)
            default = self._pydantic_default_for(field)
            field_definitions[field.name] = (python_type, default)

        return create_model(
            "ResolvedConfig",
            __config__=ConfigDict(frozen=True),
            **field_definitions,
        )

    def _python_type_for(self, field: Field) -> Any:
        if field.kind is FieldKind.ENUM:
            assert field.enum_class is not None  # noqa: S101 — garantido por Field.__post_init__
            return field.enum_class
        if field.kind is FieldKind.LIST:
            assert field.item_kind is not None  # noqa: S101 — garantido por Field.__post_init__
            item_type = _SIMPLE_KIND_TO_TYPE[field.item_kind]
            return list[item_type]  # type: ignore[valid-type]
        return _SIMPLE_KIND_TO_TYPE[field.kind]

    def _pydantic_default_for(self, field: Field) -> Any:
        if field.required:
            return ...  # Ellipsis: sintaxe do Pydantic para "campo obrigatório"
        if isinstance(field.default, SecretValue):
            return field.default.reveal()
        return field.default

    def _prepare_list_fields(
        self, schema: Schema, raw_values: Mapping[str, str]
    ) -> dict[str, Any]:
        prepared: dict[str, Any] = dict(raw_values)
        for field in schema.fields:
            if field.kind is FieldKind.LIST and field.name in prepared:
                raw = prepared[field.name]
                if isinstance(raw, str):
                    prepared[field.name] = [
                        item.strip() for item in raw.split(",") if item.strip()
                    ]
        return prepared

    def _wrap_secrets(self, schema: Schema, resolved: dict[str, Any]) -> dict[str, Any]:
        wrapped = dict(resolved)
        for field in schema.fields:
            if (
                field.secret
                and field.name in wrapped
                and not isinstance(wrapped[field.name], SecretValue)
            ):
                wrapped[field.name] = SecretValue(wrapped[field.name])
        return wrapped
