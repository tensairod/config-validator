"""Monta o objeto de configuração final, com atributos aninhados (RF07).

Este é o último passo do pipeline: Loader (lê fontes brutas) -> Validator
(valida e tipa) -> ConfigBuilder (monta a árvore de atributos aninhados
a partir do Schema.namespace_tree).

Um ConfigBuilder consome o dict PLANO devolvido pelo Validator (ex:
{"db__host": "localhost", "db__port": 5432}) e devolve uma árvore de
ConfigNamespace navegável por atributo (`config.db.host`,
`config.db.port`), resolvendo os namespaces declarados via o separador
'__' no nome dos campos (ver Schema.namespace_tree).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from config_validator.domain.field import Field
from config_validator.domain.schema import Schema


class ConfigNamespace:
    """Nó imutável de configuração, navegável por atributo.

    Uma instância pode representar tanto a raiz do objeto de configuração
    quanto um namespace intermediário (ex: o `db` em `config.db.host`).
    Folhas são sempre valores já validados e tipados pelo Validator
    (incluindo SecretValue, quando aplicável) — nunca outro
    ConfigNamespace aninhado incorretamente.
    """

    def __init__(self, values: Mapping[str, Any]) -> None:
        # object.__setattr__ é necessário aqui porque __setattr__ é
        # bloqueado abaixo para garantir imutabilidade externa.
        object.__setattr__(self, "_values", dict(values))

    def __getattr__(self, name: str) -> Any:
        # __getattr__ (diferente de __getattribute__) só é chamado quando
        # a busca normal de atributo falha — então isto não entra em
        # recursão ao acessar self._values.
        try:
            return self._values[name]
        except KeyError as exc:
            raise AttributeError(
                f"Config não possui o campo ou namespace {name!r}."
            ) from exc

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(
            "Config é imutável — não é possível definir ou alterar atributos "
            f"após a construção (tentativa de definir {name!r})."
        )

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ConfigNamespace):
            return bool(self._values == other._values)
        return NotImplemented

    def __repr__(self) -> str:
        items = ", ".join(self._repr_items())
        return f"ConfigNamespace({items})"

    def _repr_items(self, prefix: str = "") -> list[str]:
        """Gera os pares 'chave=valor' já achatados, usando notação de
        ponto para namespaces aninhados (ex: 'db.host=...'), em vez de
        aninhar 'ConfigNamespace(...)' dentro de outro — isso fica muito
        mais legível quando há vários níveis de namespace.
        """
        items: list[str] = []
        for key, value in self._values.items():
            full_key = f"{prefix}{key}"
            if isinstance(value, ConfigNamespace):
                items.extend(value._repr_items(prefix=f"{full_key}."))  # noqa: SLF001
            else:
                items.append(f"{full_key}={value!r}")
        return items


class ConfigBuilder:
    """Constrói a árvore final de ConfigNamespace a partir de um Schema e
    do dict plano de valores já validados (saída do Validator).
    """

    def build(self, schema: Schema, resolved_values: Mapping[str, Any]) -> ConfigNamespace:
        return self._build_namespace(schema.namespace_tree, resolved_values)

    def _build_namespace(
        self, tree: Mapping[str, Any], resolved_values: Mapping[str, Any]
    ) -> ConfigNamespace:
        values: dict[str, Any] = {}
        for key, node in tree.items():
            if isinstance(node, Field):
                values[key] = resolved_values[node.name]
            else:
                # node é um sub-dict (namespace intermediário) — recursão.
                values[key] = self._build_namespace(node, resolved_values)
        return ConfigNamespace(values)
