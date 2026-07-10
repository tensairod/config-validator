"""Suporte a validações cruzadas entre múltiplos campos (RF04).

Uma validação cruzada expressa uma regra que depende do valor de mais de
um campo ao mesmo tempo — por exemplo, "se ENV=production, DEBUG deve ser
false". Isso não pode ser expresso pela validação individual de um único
Field (que só conhece seu próprio tipo e obrigatoriedade), por isso vive
como um conceito à parte no domínio.

Importante: um CrossValidator opera sobre valores JÁ resolvidos e tipados
(o dict final, pós-parsing) — não faz parsing nem coerção de tipos. Isso
mantém a responsabilidade de cada peça clara: Field/Schema descrevem
estrutura, CrossValidator descreve regras de negócio sobre os valores.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

CrossValidatorFunc = Callable[[Mapping[str, Any]], str | None]


@dataclass(frozen=True)
class CrossValidator:
    """Uma regra de validação cruzada nomeada.

    Args:
        name: identificador único da regra. Usado em mensagens de erro e
            para detectar duplicatas dentro de um Schema.
        check: função que recebe o dict de valores já resolvidos de todos
            os campos do Schema, e retorna uma mensagem de erro (str) se a
            regra for violada, ou None se estiver tudo certo.
        description: texto usado na documentação gerada (RF06).

    Raises:
        ValueError: se `name` for vazio.
    """

    name: str
    check: CrossValidatorFunc
    description: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("CrossValidator.name não pode ser vazio.")

    def run(self, values: Mapping[str, Any]) -> str | None:
        """Executa a regra contra os valores fornecidos.

        Não captura exceções vindas de `check` — se a própria regra tem
        um bug (ex: acessa uma chave inexistente sem usar .get()), isso
        deve estourar como um erro de programação da regra, não ser
        silenciosamente tratado como "configuração inválida".
        """
        return self.check(values)


def cross_validator(
    name: str, description: str = ""
) -> Callable[[CrossValidatorFunc], CrossValidator]:
    """Decorator para declarar uma validação cruzada de forma ergonômica.

    Exemplo:
        @cross_validator(
            name="debug_disabled_in_production",
            description="DEBUG deve ser false quando ENV=production.",
        )
        def check_debug(values):
            if values.get("env") == "production" and values.get("debug") is True:
                return "DEBUG deve ser false quando ENV=production."
            return None
    """

    def decorator(func: CrossValidatorFunc) -> CrossValidator:
        return CrossValidator(name=name, check=func, description=description)

    return decorator
