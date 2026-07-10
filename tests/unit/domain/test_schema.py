"""Testes unitários para config_validator.domain.schema.Schema."""

import pytest

from config_validator.domain.cross_validator import CrossValidator, cross_validator
from config_validator.domain.field import Field, FieldKind
from config_validator.domain.schema import Schema


def _str_field(name: str, **kwargs: object) -> Field:
    return Field(name=name, kind=FieldKind.STR, **kwargs)  # type: ignore[arg-type]


class TestSchemaHappyPath:
    def test_schema_with_flat_fields(self) -> None:
        schema = Schema.of(_str_field("database_url"), _str_field("api_key"))
        assert len(schema) == 2

    def test_schema_iteration_preserves_order(self) -> None:
        f1, f2, f3 = _str_field("a"), _str_field("b"), _str_field("c")
        schema = Schema.of(f1, f2, f3)
        assert list(schema) == [f1, f2, f3]

    def test_get_field_found(self) -> None:
        f = _str_field("database_url")
        schema = Schema.of(f)
        assert schema.get_field("database_url") is f

    def test_get_field_not_found_raises(self) -> None:
        schema = Schema.of(_str_field("database_url"))
        with pytest.raises(KeyError):
            schema.get_field("does_not_exist")

    def test_empty_schema_is_allowed(self) -> None:
        schema = Schema.of()
        assert len(schema) == 0


class TestSchemaNamespaces:
    def test_single_level_namespace_tree(self) -> None:
        host = _str_field("db__host")
        port = _str_field("db__port")
        schema = Schema.of(host, port)
        assert schema.namespace_tree == {"db": {"host": host, "port": port}}

    def test_multi_level_namespace_tree(self) -> None:
        size = _str_field("db__pool__size")
        schema = Schema.of(size)
        assert schema.namespace_tree == {"db": {"pool": {"size": size}}}

    def test_mixed_flat_and_namespaced_fields(self) -> None:
        flat = _str_field("debug")
        nested = _str_field("db__host")
        schema = Schema.of(flat, nested)
        assert schema.namespace_tree == {"debug": flat, "db": {"host": nested}}

    def test_two_separate_namespaces(self) -> None:
        db_host = _str_field("db__host")
        cache_host = _str_field("cache__host")
        schema = Schema.of(db_host, cache_host)
        tree = schema.namespace_tree
        assert tree["db"]["host"] is db_host
        assert tree["cache"]["host"] is cache_host


class TestSchemaCrossValidators:
    def test_schema_without_cross_validators_defaults_to_empty(self) -> None:
        schema = Schema.of(_str_field("a"))
        assert schema.cross_validators == ()
        assert schema.run_cross_validators({"a": "x"}) == []

    def test_duplicate_cross_validator_name_raises(self) -> None:
        cv1 = CrossValidator(name="rule", check=lambda values: None)
        cv2 = CrossValidator(name="rule", check=lambda values: None)
        with pytest.raises(ValueError, match="CrossValidator duplicado"):
            Schema.of(_str_field("a"), cross_validators=(cv1, cv2))

    def test_run_cross_validators_aggregates_all_violations(self) -> None:
        @cross_validator(name="rule_1")
        def check_1(values: dict) -> str | None:  # type: ignore[type-arg]
            return "erro 1" if values.get("x") else None

        @cross_validator(name="rule_2")
        def check_2(values: dict) -> str | None:  # type: ignore[type-arg]
            return "erro 2" if values.get("y") else None

        schema = Schema.of(_str_field("x"), _str_field("y"), cross_validators=(check_1, check_2))
        errors = schema.run_cross_validators({"x": True, "y": True})
        assert errors == ["erro 1", "erro 2"]

    def test_run_cross_validators_returns_empty_when_all_pass(self) -> None:
        @cross_validator(name="rule")
        def check(values: dict) -> str | None:  # type: ignore[type-arg]
            return "erro" if values.get("x") else None

        schema = Schema.of(_str_field("x"), cross_validators=(check,))
        assert schema.run_cross_validators({"x": False}) == []


class TestSchemaValidationErrors:
    def test_duplicate_field_name_raises(self) -> None:
        with pytest.raises(ValueError, match="Campo duplicado"):
            Schema.of(_str_field("database_url"), _str_field("database_url"))

    def test_scalar_field_colliding_with_namespace_prefix_raises(self) -> None:
        # 'db' é um campo escalar, mas 'db__host' tenta usar 'db' como namespace.
        with pytest.raises(ValueError, match="Conflito de namespace"):
            Schema.of(_str_field("db"), _str_field("db__host"))

    def test_collision_detected_regardless_of_field_order(self) -> None:
        with pytest.raises(ValueError, match="Conflito de namespace"):
            Schema.of(_str_field("db__host"), _str_field("db"))

    def test_deep_namespace_collision_raises(self) -> None:
        # 'db__pool' colide com 'db__pool__size' (nível intermediário).
        with pytest.raises(ValueError, match="Conflito de namespace"):
            Schema.of(_str_field("db__pool"), _str_field("db__pool__size"))
