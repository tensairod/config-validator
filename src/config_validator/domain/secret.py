"""Wrapper para valores de configuração sensíveis (RF05).

Um `SecretValue` nunca revela seu conteúdo via `repr()`, `str()`, f-strings,
ou quando aparece dentro de outra estrutura impressa (tupla, lista, dict,
traceback de exceção). O valor real só é acessível explicitamente através
de `reveal()` — isso torna o vazamento acidental de segredos em logs algo
que exige um ato deliberado do desenvolvedor, não um acidente de printar
o objeto errado durante um debug.
"""

from __future__ import annotations

from typing import Any

_MASK = "**********"


class SecretValue:
    """Envelope opaco em torno de um valor sensível (API key, senha, token).

    Note que isto NÃO é criptografia — é uma proteção contra vazamento
    acidental via repr/str/logging, não contra acesso deliberado ao
    processo em memória. Segredos ainda devem ser gerenciados com um
    secrets manager em produção; esta classe resolve o problema mais
    comum e mais bobo: `logger.info(f"Config carregada: {config}")`
    vazando uma API key inteira no stdout.
    """

    __slots__ = ("_value",)

    def __init__(self, value: Any) -> None:
        self._value = value

    def reveal(self) -> Any:
        """Retorna o valor real. Único método que expõe o conteúdo —
        o nome é intencionalmente explícito para que o uso apareça de
        forma óbvia em code review.
        """
        return self._value

    def __repr__(self) -> str:
        return f"SecretValue({_MASK!r})"

    def __str__(self) -> str:
        return _MASK

    def __format__(self, format_spec: str) -> str:
        # Garante que f"{secret}" e "{}".format(secret) também mascarem,
        # em vez de cair no __repr__ ou delegar para o valor real.
        return _MASK

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SecretValue):
            return bool(self._value == other._value)
        return NotImplemented

    # Deliberadamente NÃO hashable: um SecretValue não deve ser usado como
    # chave de dict (poderia acabar sendo exposto em repr de estruturas
    # maiores de forma menos óbvia que um valor direto).
    __hash__ = None  # type: ignore[assignment]
