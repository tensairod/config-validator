"""Testes unitários para config_validator.domain.field.Field.

Cobertura visada: 100% — esta é a classe mais fundamental do domínio,
e cada regra de validação aqui evita uma classe inteira de bugs de
configuração em produção.
"""

from dataclasses import FrozenInstanceError
from enum import Enum

import pytest

from config_validator.domain.field import UNSET, Field, FieldKind
from config_validator.domain.secret import SecretValue


class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class TestFieldHappyPath:
    def test_required_field_without_default(self) -> None:
        field = Field(name="database_url", kind=FieldKind.STR)
        assert field.required is True
        assert field.has_default is False
        assert field.default is UNSET

    def test_optional_field_with_default(self) -> None:
        field = Field(name="debug", kind=FieldKind.BOOL, required=False, default=False)
        assert field.required is False
        assert field.has_default is True
        assert field.default is False

    def test_optional_field_with_none_as_legitimate_default(self) -> None:
        # None é um default legítimo e diferente de "nenhum default" (UNSET).
        field = Field(name="proxy_url", kind=FieldKind.STR, required=False, default=None)
        assert field.has_default is True
        assert field.default is None

    def test_list_field_defaults_item_kind_to_str(self) -> None:
        field = Field(name="allowed_hosts", kind=FieldKind.LIST, required=False, default=[])
        assert field.item_kind is FieldKind.STR

    def test_list_field_with_explicit_item_kind(self) -> None:
        field = Field(
            name="allowed_ports",
            kind=FieldKind.LIST,
            item_kind=FieldKind.INT,
            required=False,
            default=[],
        )
        assert field.item_kind is FieldKind.INT

    def test_enum_field_with_enum_class(self) -> None:
        field = Field(name="env", kind=FieldKind.ENUM, enum_class=Environment)
        assert field.enum_class is Environment

    def test_secret_field(self) -> None:
        field = Field(name="api_key", kind=FieldKind.STR, secret=True)
        assert field.secret is True

    def test_description_is_stored(self) -> None:
        field = Field(name="timeout", kind=FieldKind.INT, description="Timeout em segundos.")
        assert field.description == "Timeout em segundos."


class TestFieldValidationErrors:
    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError, match="não pode ser vazio"):
            Field(name="", kind=FieldKind.STR)

    @pytest.mark.parametrize("invalid_name", ["123abc", "has space", "has-dash", "has.dot"])
    def test_non_identifier_name_raises(self, invalid_name: str) -> None:
        with pytest.raises(ValueError, match="identificador Python válido"):
            Field(name=invalid_name, kind=FieldKind.STR)

    def test_enum_kind_without_enum_class_raises(self) -> None:
        with pytest.raises(ValueError, match="não recebeu 'enum_class'"):
            Field(name="env", kind=FieldKind.ENUM)

    def test_non_enum_kind_with_enum_class_raises(self) -> None:
        with pytest.raises(ValueError, match="não FieldKind.ENUM"):
            Field(name="env", kind=FieldKind.STR, enum_class=Environment)

    def test_non_list_kind_with_item_kind_raises(self) -> None:
        with pytest.raises(ValueError, match="não FieldKind.LIST"):
            Field(name="port", kind=FieldKind.INT, item_kind=FieldKind.STR)

    def test_optional_without_default_raises(self) -> None:
        with pytest.raises(ValueError, match="não tem 'default'"):
            Field(name="debug", kind=FieldKind.BOOL, required=False)

    def test_required_with_default_raises(self) -> None:
        with pytest.raises(ValueError, match="recebeu um 'default'"):
            Field(name="database_url", kind=FieldKind.STR, required=True, default="postgres://")


class TestFieldImmutability:
    def test_field_is_frozen(self) -> None:
        field = Field(name="port", kind=FieldKind.INT)
        with pytest.raises(FrozenInstanceError):
            field.name = "other_port"  # type: ignore[misc]


class TestFieldSecretDefault:
    def test_secret_field_with_default_is_wrapped_in_secret_value(self) -> None:
        field = Field(
            name="api_key", kind=FieldKind.STR, required=False, default="raw-key", secret=True
        )
        assert isinstance(field.default, SecretValue)
        assert field.default.reveal() == "raw-key"

    def test_secret_field_default_never_leaks_via_repr(self) -> None:
        field = Field(
            name="api_key", kind=FieldKind.STR, required=False, default="raw-key", secret=True
        )
        assert "raw-key" not in repr(field)

    def test_secret_field_without_default_is_not_wrapped(self) -> None:
        # required=True não tem default (UNSET) — nada para envolver.
        field = Field(name="api_key", kind=FieldKind.STR, secret=True)
        assert field.default is UNSET

    def test_non_secret_field_default_stays_raw(self) -> None:
        field = Field(name="timeout", kind=FieldKind.INT, required=False, default=30)
        assert field.default == 30
        assert not isinstance(field.default, SecretValue)

    def test_passing_secret_value_directly_is_not_double_wrapped(self) -> None:
        pre_wrapped = SecretValue("raw-key")
        field = Field(
            name="api_key", kind=FieldKind.STR, required=False, default=pre_wrapped, secret=True
        )
        assert field.default is pre_wrapped


class TestUnsetSentinel:
    """UNSET é um detalhe de implementação, mas seu comportamento (repr e
    truthiness) é observável publicamente via `Field.default`, então vale
    testar diretamente para fechar cobertura e documentar o contrato.
    """

    def test_unset_repr_is_readable(self) -> None:
        assert repr(UNSET) == "<UNSET>"

    def test_unset_is_falsy(self) -> None:
        assert bool(UNSET) is False
