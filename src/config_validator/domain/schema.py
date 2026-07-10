"""Agrupa múltiplos Fields em um schema de configuração completo.

Resolve namespaces (RF07): campos cujo nome usa '__' como separador
(ex: 'db__host') são tratados como pertencentes a um namespace aninhado.
A resolução final em objetos Python aninhados (`config.db.host`) acontece
na camada de Application — aqui só construímos a árvore de namespaces e
validamos consistência.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any

from config_validator.domain.cross_validator import CrossValidator
from config_validator.domain.field import Field

NAMESPACE_SEPARATOR = "__"


@dataclass(frozen=True)
class Schema:
    """Representa o conjunto completo de campos de configuração esperados
    por uma aplicação, incluindo eventuais regras de validação cruzada.

    Args:
        fields: os campos que compõem o schema. A ordem é preservada (útil
            para a geração de documentação em ordem previsível, RF06).
        cross_validators: regras de validação cruzada (RF04), executadas
            após a validação individual de cada campo.

    Raises:
        ValueError: se houver nomes de campo duplicados, colisão de
            namespace, ou nomes de CrossValidator duplicados.
    """

    fields: tuple[Field, ...]
    cross_validators: tuple[CrossValidator, ...] = ()

    def __post_init__(self) -> None:
        self._validate_no_duplicate_names()
        self._validate_no_namespace_collisions()
        self._validate_no_duplicate_cross_validator_names()

    @classmethod
    def of(
        cls,
        *fields: Field,
        cross_validators: tuple[CrossValidator, ...] = (),
    ) -> Schema:
        """Atalho ergonômico: Schema.of(field1, field2, cross_validators=(...))
        em vez de Schema(fields=(field1, field2), cross_validators=(...)).
        """
        return cls(fields=tuple(fields), cross_validators=cross_validators)

    def _validate_no_duplicate_cross_validator_names(self) -> None:
        seen: set[str] = set()
        for cv in self.cross_validators:
            if cv.name in seen:
                raise ValueError(
                    f"CrossValidator duplicado no Schema: {cv.name!r}. Cada regra de "
                    "validação cruzada deve ter um nome único."
                )
            seen.add(cv.name)

    def run_cross_validators(self, values: Mapping[str, Any]) -> list[str]:
        """Executa todas as validações cruzadas e agrega as mensagens de
        erro de todas as regras violadas (ADR-004: erros agregados, não
        fail-fast na primeira regra).
        """
        errors: list[str] = []
        for cv in self.cross_validators:
            message = cv.run(values)
            if message is not None:
                errors.append(message)
        return errors

    def _validate_no_duplicate_names(self) -> None:
        seen: set[str] = set()
        for f in self.fields:
            if f.name in seen:
                raise ValueError(
                    f"Campo duplicado no Schema: {f.name!r}. Cada nome de campo "
                    "deve aparecer no máximo uma vez."
                )
            seen.add(f.name)

    def _validate_no_namespace_collisions(self) -> None:
        names = {f.name for f in self.fields}
        for name in names:
            parts = name.split(NAMESPACE_SEPARATOR)
            for i in range(1, len(parts)):
                prefix = NAMESPACE_SEPARATOR.join(parts[:i])
                if prefix in names:
                    raise ValueError(
                        f"Conflito de namespace no Schema: {prefix!r} é um campo escalar "
                        f"e, ao mesmo tempo, prefixo de namespace de {name!r}. "
                        "Um nome não pode ser as duas coisas — renomeie um dos dois."
                    )

    @property
    def namespace_tree(self) -> dict[str, Any]:
        """Retorna a estrutura aninhada de namespaces como um dict.

        Exemplo: campos 'db__host' e 'db__port' geram
        {'db': {'host': Field(...), 'port': Field(...)}}.
        Campos sem '__' no nome ficam na raiz da árvore.
        Usado pela camada de Application para montar o objeto de
        configuração final com atributos aninhados (`config.db.host`).
        """
        tree: dict[str, Any] = {}
        for f in self.fields:
            parts = f.name.split(NAMESPACE_SEPARATOR)
            node = tree
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = f
        return tree

    def get_field(self, name: str) -> Field:
        """Busca um campo pelo nome completo (incluindo namespace, ex: 'db__host')."""
        for f in self.fields:
            if f.name == name:
                return f
        raise KeyError(f"Campo {name!r} não existe neste Schema.")

    def __len__(self) -> int:
        return len(self.fields)

    def __iter__(self) -> Iterator[Field]:
        return iter(self.fields)
