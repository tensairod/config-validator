"""Interface que toda fonte de configuração deve implementar (ADR-002).

Definida na camada de Application — não em Infrastructure — porque é a
Application (o futuro `Loader`) que depende desta abstração. As
implementações concretas (`EnvVarSource`, `DotEnvSource`) vivem em
Infrastructure e a implementam. Isso é o Dependency Inversion Principle
na prática: o código de alto nível (Loader) não depende de detalhes de
baixo nível (como ler um arquivo .env) — ambos dependem desta interface.

Usamos `typing.Protocol` (tipagem estrutural) em vez de uma classe
abstrata (ABC) porque não há nenhum comportamento compartilhado para
herdar — só um contrato de método. Protocol também permite que qualquer
objeto com um método `load()` compatível seja aceito, sem precisar herdar
explicitamente desta classe (duck typing verificável estaticamente).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ConfigSource(Protocol):
    """Uma fonte de onde valores brutos de configuração podem ser lidos."""

    def load(self) -> dict[str, str]:
        """Carrega os valores brutos (ainda não validados/tipados) desta fonte.

        Returns:
            Um dict simples de nome -> valor em string. A validação e
            coerção de tipos (para int, bool, etc.) acontecem depois, no
            Validator — uma fonte não sabe nem precisa saber o Schema.
            Se a fonte estiver vazia ou inacessível (ex: arquivo .env que
            não existe), deve retornar um dict vazio, nunca lançar exceção
            — a ausência de uma fonte não é um erro, é uma fonte com zero
            valores.
        """
        ...
