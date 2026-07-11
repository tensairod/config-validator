"""Testes unitários para config_validator.application.validator.Validator."""

from enum import Enum

import pytest

from config_validator.application.errors import ConfigValidationError
from config_validator.application.validator import Validator
from config_validator.domain.cross_validator import cross_validator
from config_validator.domain.field import Field, FieldKind
from config_validator.domain.schema import Schema
from config_validator.domain.secret import SecretValue


class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class TestValidatorHappyPath:
    def test_validates_and_coerces_simple_types(self) -> None:
        schema = Schema.of(
            Field(name="database_url", kind=FieldKind.STR),
            Field(name="port", kind=FieldKind.INT),
            Field(name="debug", kind=FieldKind.BOOL),
            Field(name="timeout", kind=FieldKind.FLOAT),
        )
        raw = {
            "database_url": "postgres://localhost",
            "port": "5432",
            "debug": "false",
            "timeout": "1.5",
        }

        result = Validator().validate(schema, raw)

        assert result == {
            "database_url": "postgres://localhost",
            "port": 5432,
            "debug": False,
            "timeout": 1.5,
        }
        assert isinstance(result["port"], int)
        assert isinstance(result["debug"], bool)
        assert isinstance(result["timeout"], float)

    def test_optional_field_uses_default_when_missing(self) -> None:
        schema = Schema.of(Field(name="debug", kind=FieldKind.BOOL, required=False, default=False))

        result = Validator().validate(schema, {})

        assert result == {"debug": False}

    def test_enum_field(self) -> None:
        schema = Schema.of(Field(name="env", kind=FieldKind.ENUM, enum_class=Environment))

        result = Validator().validate(schema, {"env": "production"})

        assert result["env"] is Environment.PRODUCTION

    def test_list_field_splits_comma_separated_string(self) -> None:
        schema = Schema.of(Field(name="allowed_hosts", kind=FieldKind.LIST))

        result = Validator().validate(schema, {"allowed_hosts": "a.com, b.com,c.com"})

        assert result["allowed_hosts"] == ["a.com", "b.com", "c.com"]

    def test_list_field_of_ints(self) -> None:
        schema = Schema.of(
            Field(name="allowed_ports", kind=FieldKind.LIST, item_kind=FieldKind.INT)
        )

        result = Validator().validate(schema, {"allowed_ports": "80,443,8080"})

        assert result["allowed_ports"] == [80, 443, 8080]

    def test_url_field(self) -> None:
        schema = Schema.of(Field(name="webhook_url", kind=FieldKind.URL))

        result = Validator().validate(schema, {"webhook_url": "https://example.com/hook"})

        assert str(result["webhook_url"]) == "https://example.com/hook"

    def test_path_field(self) -> None:
        schema = Schema.of(Field(name="log_path", kind=FieldKind.PATH))

        result = Validator().validate(schema, {"log_path": "/var/log/app.log"})

        assert str(result["log_path"]) == "/var/log/app.log"


    def test_list_field_accepts_pre_split_list_not_just_raw_string(self) -> None:
        # Cobre o caso de um chamador que já monta a lista programaticamente
        # (não vindo de uma fonte de string bruta como env var/.env).
        schema = Schema.of(Field(name="allowed_hosts", kind=FieldKind.LIST))

        result = Validator().validate(schema, {"allowed_hosts": ["a.com", "b.com"]})  # type: ignore[dict-item]

        assert result["allowed_hosts"] == ["a.com", "b.com"]


class TestValidatorFieldErrors:
    def test_missing_required_field_raises_with_actionable_message(self) -> None:
        schema = Schema.of(Field(name="database_url", kind=FieldKind.STR))

        with pytest.raises(ConfigValidationError) as exc_info:
            Validator().validate(schema, {})

        assert len(exc_info.value.errors) == 1
        assert "'database_url'" in exc_info.value.errors[0]
        assert "obrigatório" in exc_info.value.errors[0]

    def test_invalid_int_raises_with_actionable_message(self) -> None:
        schema = Schema.of(Field(name="port", kind=FieldKind.INT))

        with pytest.raises(ConfigValidationError) as exc_info:
            Validator().validate(schema, {"port": "not-a-number"})

        assert "número inteiro válido" in exc_info.value.errors[0]

    def test_invalid_bool_raises_with_actionable_message(self) -> None:
        schema = Schema.of(Field(name="debug", kind=FieldKind.BOOL))

        with pytest.raises(ConfigValidationError) as exc_info:
            Validator().validate(schema, {"debug": "maybe"})

        assert "booleano válido" in exc_info.value.errors[0]

    def test_invalid_enum_lists_accepted_values(self) -> None:
        schema = Schema.of(Field(name="env", kind=FieldKind.ENUM, enum_class=Environment))

        with pytest.raises(ConfigValidationError) as exc_info:
            Validator().validate(schema, {"env": "not-a-real-env"})

        assert "Valores aceitos" in exc_info.value.errors[0]

    def test_multiple_errors_are_aggregated_not_fail_fast(self) -> None:
        schema = Schema.of(
            Field(name="database_url", kind=FieldKind.STR),
            Field(name="port", kind=FieldKind.INT),
            Field(name="debug", kind=FieldKind.BOOL),
        )

        with pytest.raises(ConfigValidationError) as exc_info:
            # database_url ausente, port inválido, debug inválido — 3 erros de uma vez.
            Validator().validate(schema, {"port": "abc", "debug": "maybe"})

        assert len(exc_info.value.errors) == 3

    def test_field_description_appears_in_error_message(self) -> None:
        schema = Schema.of(
            Field(
                name="database_url",
                kind=FieldKind.STR,
                description="URL de conexão com o PostgreSQL.",
            )
        )

        with pytest.raises(ConfigValidationError) as exc_info:
            Validator().validate(schema, {})

        assert "URL de conexão com o PostgreSQL." in exc_info.value.errors[0]


class TestValidatorCrossValidation:
    def test_cross_validator_violation_raises(self) -> None:
        rule = cross_validator(name="debug_disabled_in_production")(
            lambda values: (
                "DEBUG deve ser false em produção."
                if values.get("env") == Environment.PRODUCTION and values.get("debug") is True
                else None
            )
        )
        schema = Schema.of(
            Field(name="env", kind=FieldKind.ENUM, enum_class=Environment),
            Field(name="debug", kind=FieldKind.BOOL),
            cross_validators=(rule,),
        )

        with pytest.raises(ConfigValidationError) as exc_info:
            Validator().validate(schema, {"env": "production", "debug": "true"})

        assert exc_info.value.errors == ["DEBUG deve ser false em produção."]

    def test_cross_validator_passes_when_rule_satisfied(self) -> None:
        rule = cross_validator(name="debug_disabled_in_production")(
            lambda values: (
                "DEBUG deve ser false em produção."
                if values.get("env") == Environment.PRODUCTION and values.get("debug") is True
                else None
            )
        )
        schema = Schema.of(
            Field(name="env", kind=FieldKind.ENUM, enum_class=Environment),
            Field(name="debug", kind=FieldKind.BOOL),
            cross_validators=(rule,),
        )

        result = Validator().validate(schema, {"env": "production", "debug": "false"})

        assert result == {"env": Environment.PRODUCTION, "debug": False}

    def test_cross_validators_are_not_run_when_field_validation_fails(self) -> None:
        # Decisão de design: se a validação de campo já falhou, não faz
        # sentido rodar regras cruzadas sobre um dict incompleto/inválido.
        # Só os erros de campo devem aparecer aqui.
        rule = cross_validator(name="always_fails")(lambda values: "não deveria rodar")
        schema = Schema.of(
            Field(name="port", kind=FieldKind.INT),
            cross_validators=(rule,),
        )

        with pytest.raises(ConfigValidationError) as exc_info:
            Validator().validate(schema, {"port": "not-a-number"})

        assert "não deveria rodar" not in exc_info.value.errors
        assert any("número inteiro válido" in error for error in exc_info.value.errors)


class TestValidatorSecretWrapping:
    def test_secret_field_value_is_wrapped_in_secret_value(self) -> None:
        schema = Schema.of(Field(name="api_key", kind=FieldKind.STR, secret=True))

        result = Validator().validate(schema, {"api_key": "sk-real-secret-value"})

        assert isinstance(result["api_key"], SecretValue)
        assert result["api_key"].reveal() == "sk-real-secret-value"

    def test_secret_field_never_leaks_via_repr_of_result(self) -> None:
        schema = Schema.of(Field(name="api_key", kind=FieldKind.STR, secret=True))

        result = Validator().validate(schema, {"api_key": "sk-real-secret-value"})

        assert "sk-real-secret-value" not in repr(result)

    def test_secret_field_with_default_is_wrapped_too(self) -> None:
        schema = Schema.of(
            Field(
                name="api_key", kind=FieldKind.STR, required=False, default="fallback", secret=True
            )
        )

        result = Validator().validate(schema, {})

        assert isinstance(result["api_key"], SecretValue)
        assert result["api_key"].reveal() == "fallback"

    def test_non_secret_field_stays_raw(self) -> None:
        schema = Schema.of(Field(name="port", kind=FieldKind.INT))

        result = Validator().validate(schema, {"port": "8080"})

        assert not isinstance(result["port"], SecretValue)
