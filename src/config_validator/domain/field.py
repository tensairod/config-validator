"""Modela um único campo de configuração esperado por uma aplicação.

Este módulo é a base da camada de Domain (ver docs/architecture.md).
Propositalmente não importa Pydantic, dotenv, nem nada de I/O — a validação
real de tipos acontece na camada de Application (ADR-001). Isso é o que
permite testar 100% da lógica de negócio de "o que é um campo válido" sem
precisar de env vars reais, arquivos .env, ou mocks pesados.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class FieldKind(Enum):
    """Tipos de dado suportados por um campo de configuração (RF02).

    Mantido como um Enum próprio — em vez de usar tipos Python diretamente
    (`str`, `int`) ou tipos do Pydantic (`AnyUrl`) — para que o domínio não
    dependa de nenhuma biblioteca de validação específica (ADR-002). A
    tradução de FieldKind para um tipo concreto do Pydantic acontece no
    Validator, na camada de Application.
    """

    STR = "str"
    INT = "int"
    BOOL = "bool"
    FLOAT = "float"
    LIST = "list"
    ENUM = "enum"
    URL = "url"
    PATH = "path"


class _Unset:
    """Sentinela interna usada para distinguir 'nenhum default fornecido'
    de 'default=None' (que é um valor legítimo para um campo opcional).
    """

    def __repr__(self) -> str:
        return "<UNSET>"

    def __bool__(self) -> bool:
        return False


UNSET: Any = _Unset()


@dataclass(frozen=True)
class Field:
    """Representa um único campo de configuração.

    Um `Field` descreve *o que* é esperado (nome, tipo, obrigatoriedade,
    default, descrição) — não *como* validar. Essa separação é o que torna
    o domínio testável isoladamente (ver ADR-001 em docs/adr/).

    Args:
        name: nome do campo. Deve ser um identificador Python válido, pois
            vira atributo do objeto de configuração final (ex: `config.database_url`).
        kind: tipo de dado esperado (ver FieldKind).
        required: se True, o campo precisa estar presente em alguma fonte
            (env var ou .env). Se False, precisa de um `default`.
        default: valor usado quando o campo é opcional e não foi fornecido.
            Use o sentinel UNSET (implícito, não precisa passar) para campos
            obrigatórios.
        description: texto usado na geração de documentação (RF06) e em
            mensagens de erro.
        secret: se True, o valor nunca deve aparecer em repr/logs/tracebacks (RF05).
        enum_class: obrigatório quando kind=FieldKind.ENUM; a classe Enum
            que define os valores válidos.
        item_kind: usado apenas quando kind=FieldKind.LIST, define o tipo
            de cada item da lista. Default: FieldKind.STR.

    Raises:
        ValueError: se qualquer combinação de argumentos for inconsistente.
            Todas as regras são validadas na criação (fail-fast), nunca em
            uso posterior do campo.
    """

    name: str
    kind: FieldKind
    required: bool = True
    default: Any = UNSET
    description: str = ""
    secret: bool = False
    enum_class: type[Enum] | None = None
    item_kind: FieldKind | None = None

    def __post_init__(self) -> None:
        self._validate_name()
        self._validate_enum_consistency()
        self._normalize_and_validate_list_consistency()
        self._validate_required_vs_default()

    def _validate_name(self) -> None:
        if not self.name:
            raise ValueError("Field.name não pode ser vazio.")
        if not self.name.isidentifier():
            raise ValueError(
                f"Field.name={self.name!r} precisa ser um identificador Python válido "
                "(ex: 'database_url'), pois vira atributo do objeto de configuração."
            )

    def _validate_enum_consistency(self) -> None:
        if self.kind is FieldKind.ENUM and self.enum_class is None:
            raise ValueError(
                f"Field {self.name!r} é do tipo ENUM mas não recebeu 'enum_class'. "
                "Exemplo: Field(name='env', kind=FieldKind.ENUM, enum_class=Environment)"
            )
        if self.kind is not FieldKind.ENUM and self.enum_class is not None:
            raise ValueError(
                f"Field {self.name!r} recebeu 'enum_class' mas kind={self.kind.value!r}, "
                "não FieldKind.ENUM. Remova 'enum_class' ou mude o kind."
            )

    def _normalize_and_validate_list_consistency(self) -> None:
        if self.kind is FieldKind.LIST and self.item_kind is None:
            # dataclass é frozen; object.__setattr__ é a forma suportada
            # de atribuir em __post_init__.
            object.__setattr__(self, "item_kind", FieldKind.STR)
        if self.kind is not FieldKind.LIST and self.item_kind is not None:
            raise ValueError(
                f"Field {self.name!r} recebeu 'item_kind' mas kind={self.kind.value!r}, "
                "não FieldKind.LIST. Remova 'item_kind' ou mude o kind."
            )

    def _validate_required_vs_default(self) -> None:
        if not self.required and self.default is UNSET:
            raise ValueError(
                f"Field {self.name!r} está marcado como opcional (required=False) mas "
                "não tem 'default'. Campos opcionais precisam de um valor default explícito."
            )
        if self.required and self.default is not UNSET:
            raise ValueError(
                f"Field {self.name!r} está marcado como obrigatório (required=True) mas "
                "recebeu um 'default'. Marque required=False ou remova o default."
            )

    @property
    def has_default(self) -> bool:
        """Retorna True se o campo tem um valor default definido."""
        return self.default is not UNSET
