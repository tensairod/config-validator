"""Traduz erros brutos do Pydantic em mensagens acionáveis (RNF07).

Uma mensagem de erro do Pydantic puro (ex: "Input should be a valid
integer, unable to parse string as an integer") descreve o problema, mas
não é escrita pensando em quem vai ler um log de deploy às 3h da manhã.
Este módulo reescreve os tipos de erro mais comuns em português, sempre
incluindo o nome do campo e, quando disponível, a descrição cadastrada
no Field — sem depender de string matching frágil no texto do Pydantic
(usamos o campo estruturado `type` do erro, não `msg`).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from config_validator.domain.schema import Schema

# Tipos de erro do Pydantic v2 que reescrevemos com mensagens próprias.
# Referência: https://docs.pydantic.dev/latest/errors/validation_errors/
_ACTIONABLE_HINTS: dict[str, str] = {
    "int_parsing": "recebeu um valor que não é um número inteiro válido",
    "int_type": "recebeu um valor que não é um número inteiro válido",
    "float_parsing": "recebeu um valor que não é um número decimal válido",
    "float_type": "recebeu um valor que não é um número decimal válido",
    "bool_parsing": (
        "recebeu um valor que não é um booleano válido "
        "(use 'true'/'false', '1'/'0' ou 'yes'/'no')"
    ),
    "bool_type": (
        "recebeu um valor que não é um booleano válido "
        "(use 'true'/'false', '1'/'0' ou 'yes'/'no')"
    ),
    "url_parsing": "recebeu um valor que não é uma URL válida",
    "url_type": "recebeu um valor que não é uma URL válida",
    "path_type": "recebeu um valor que não é um caminho de arquivo válido",
}


def format_pydantic_errors(errors: Sequence[Mapping[str, Any]], schema: Schema) -> list[str]:
    """Formata a lista de erros brutos de um pydantic.ValidationError.errors()
    em mensagens acionáveis, uma por erro.
    """
    return [_format_single_error(error, schema) for error in errors]


def _format_single_error(error: Mapping[str, Any], schema: Schema) -> str:
    name = ".".join(str(part) for part in error["loc"])
    error_type: str = error["type"]

    try:
        field = schema.get_field(name)
    except KeyError:
        field = None

    hint_suffix = f" ({field.description})" if field and field.description else ""

    if error_type == "missing":
        return (
            f"{name!r} é obrigatório e não foi definido. Defina via variável de "
            f"ambiente ou no arquivo .env.{hint_suffix}"
        )

    if error_type == "enum":
        expected = error.get("ctx", {}).get("expected", "um dos valores permitidos")
        return f"{name!r} recebeu um valor inválido. Valores aceitos: {expected}.{hint_suffix}"

    if error_type in _ACTIONABLE_HINTS:
        return f"{name!r} {_ACTIONABLE_HINTS[error_type]}.{hint_suffix}"

    # Fallback: qualquer tipo de erro do Pydantic que ainda não mapeamos
    # explicitamente. Preferimos mostrar a mensagem original do Pydantic a
    # esconder o erro — só não é tão "amigável" quanto os casos acima.
    original_message = error["msg"]
    punctuation = "" if original_message.endswith((".", "!", "?")) else "."
    return f"{name!r}: {original_message}{punctuation}{hint_suffix}"
