"""Testes unitários para config_validator.application.config_builder."""

import pytest

from config_validator.application.config_builder import ConfigBuilder
from config_validator.domain.field import Field, FieldKind
from config_validator.domain.schema import Schema
from config_validator.domain.secret import SecretValue


class TestConfigBuilderFlatSchema:
    def test_flat_fields_become_direct_attributes(self) -> None:
        schema = Schema.of(
            Field(name="database_url", kind=FieldKind.STR),
            Field(name="port", kind=FieldKind.INT),
        )
        resolved = {"database_url": "postgres://localhost", "port": 5432}

        config = ConfigBuilder().build(schema, resolved)

        assert config.database_url == "postgres://localhost"
        assert config.port == 5432


class TestConfigBuilderNamespaces:
    def test_single_level_namespace(self) -> None:
        schema = Schema.of(
            Field(name="db__host", kind=FieldKind.STR),
            Field(name="db__port", kind=FieldKind.INT),
        )
        resolved = {"db__host": "localhost", "db__port": 5432}

        config = ConfigBuilder().build(schema, resolved)

        assert config.db.host == "localhost"
        assert config.db.port == 5432

    def test_multi_level_namespace(self) -> None:
        schema = Schema.of(Field(name="db__pool__size", kind=FieldKind.INT))
        resolved = {"db__pool__size": 10}

        config = ConfigBuilder().build(schema, resolved)

        assert config.db.pool.size == 10

    def test_mixed_flat_and_namespaced_fields(self) -> None:
        schema = Schema.of(
            Field(name="debug", kind=FieldKind.BOOL),
            Field(name="db__host", kind=FieldKind.STR),
        )
        resolved = {"debug": True, "db__host": "localhost"}

        config = ConfigBuilder().build(schema, resolved)

        assert config.debug is True
        assert config.db.host == "localhost"

    def test_two_separate_namespaces(self) -> None:
        schema = Schema.of(
            Field(name="db__host", kind=FieldKind.STR),
            Field(name="cache__host", kind=FieldKind.STR),
        )
        resolved = {"db__host": "db.local", "cache__host": "cache.local"}

        config = ConfigBuilder().build(schema, resolved)

        assert config.db.host == "db.local"
        assert config.cache.host == "cache.local"


class TestConfigNamespaceImmutabilityAndErrors:
    def test_setting_attribute_raises(self) -> None:
        schema = Schema.of(Field(name="port", kind=FieldKind.INT))
        config = ConfigBuilder().build(schema, {"port": 1})

        with pytest.raises(AttributeError, match="imutável"):
            config.port = 2  # type: ignore[misc]

    def test_accessing_unknown_attribute_raises_with_clear_message(self) -> None:
        schema = Schema.of(Field(name="port", kind=FieldKind.INT))
        config = ConfigBuilder().build(schema, {"port": 1})
        expected_message = "não possui o campo ou namespace 'does_not_exist'"

        with pytest.raises(AttributeError, match=expected_message):
            _ = config.does_not_exist


class TestConfigNamespaceEquality:
    def test_equal_configs_with_same_values(self) -> None:
        schema = Schema.of(Field(name="port", kind=FieldKind.INT))
        config_a = ConfigBuilder().build(schema, {"port": 8080})
        config_b = ConfigBuilder().build(schema, {"port": 8080})

        assert config_a == config_b

    def test_different_configs_are_not_equal(self) -> None:
        schema = Schema.of(Field(name="port", kind=FieldKind.INT))
        config_a = ConfigBuilder().build(schema, {"port": 8080})
        config_b = ConfigBuilder().build(schema, {"port": 9090})

        assert config_a != config_b

    def test_not_equal_to_unrelated_object(self) -> None:
        schema = Schema.of(Field(name="port", kind=FieldKind.INT))
        config = ConfigBuilder().build(schema, {"port": 8080})

        assert config != "not a config"

    def test_nested_namespaces_compare_by_value(self) -> None:
        schema = Schema.of(Field(name="db__host", kind=FieldKind.STR))
        config_a = ConfigBuilder().build(schema, {"db__host": "localhost"})
        config_b = ConfigBuilder().build(schema, {"db__host": "localhost"})

        assert config_a == config_b
        assert config_a.db == config_b.db


class TestConfigNamespaceRepr:
    def test_repr_shows_field_names_and_values(self) -> None:
        schema = Schema.of(Field(name="port", kind=FieldKind.INT))
        config = ConfigBuilder().build(schema, {"port": 8080})

        assert "port=8080" in repr(config)

    def test_repr_uses_dotted_path_for_single_level_namespace(self) -> None:
        schema = Schema.of(
            Field(name="debug", kind=FieldKind.BOOL),
            Field(name="db__host", kind=FieldKind.STR),
        )
        resolved = {"debug": True, "db__host": "localhost"}

        config = ConfigBuilder().build(schema, resolved)

        assert repr(config) == "ConfigNamespace(debug=True, db.host='localhost')"

    def test_repr_uses_dotted_path_for_multi_level_namespace(self) -> None:
        schema = Schema.of(Field(name="db__pool__size", kind=FieldKind.INT))
        config = ConfigBuilder().build(schema, {"db__pool__size": 10})

        assert repr(config) == "ConfigNamespace(db.pool.size=10)"

    def test_repr_of_nested_namespace_itself_is_not_prefixed(self) -> None:
        # repr(config.db) sozinho não deve carregar o prefixo 'db.' —
        # esse prefixo só existe quando visto a partir do pai.
        schema = Schema.of(Field(name="db__host", kind=FieldKind.STR))
        config = ConfigBuilder().build(schema, {"db__host": "localhost"})

        assert repr(config.db) == "ConfigNamespace(host='localhost')"

    def test_secret_field_masked_in_repr_through_the_full_tree(self) -> None:
        # Ponta a ponta: um SecretValue vindo do Validator continua mascarado
        # mesmo depois de encapsulado dentro de um ConfigNamespace aninhado.
        schema = Schema.of(Field(name="db__password", kind=FieldKind.STR, secret=True))
        resolved = {"db__password": SecretValue("super-secret")}

        config = ConfigBuilder().build(schema, resolved)

        assert "super-secret" not in repr(config)
        assert "super-secret" not in repr(config.db)
        assert config.db.password.reveal() == "super-secret"


class TestConfigNamespaceIsolation:
    def test_mutating_input_dict_after_build_does_not_affect_config(self) -> None:
        schema = Schema.of(Field(name="port", kind=FieldKind.INT))
        resolved = {"port": 8080}
        config = ConfigBuilder().build(schema, resolved)

        resolved["port"] = 9090

        assert config.port == 8080
