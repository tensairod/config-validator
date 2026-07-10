"""Testes unitários para config_validator.domain.cross_validator."""

import pytest

from config_validator.domain.cross_validator import CrossValidator, cross_validator


class TestCrossValidatorDirect:
    def test_valid_case_returns_none(self) -> None:
        cv = CrossValidator(
            name="debug_disabled_in_production",
            check=lambda values: (
                "DEBUG deve ser false em produção."
                if values.get("env") == "production" and values.get("debug") is True
                else None
            ),
        )
        assert cv.run({"env": "development", "debug": True}) is None

    def test_invalid_case_returns_message(self) -> None:
        cv = CrossValidator(
            name="debug_disabled_in_production",
            check=lambda values: (
                "DEBUG deve ser false em produção."
                if values.get("env") == "production" and values.get("debug") is True
                else None
            ),
        )
        assert cv.run({"env": "production", "debug": True}) == "DEBUG deve ser false em produção."

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError, match="não pode ser vazio"):
            CrossValidator(name="", check=lambda values: None)


class TestCrossValidatorDecorator:
    def test_decorator_builds_cross_validator_instance(self) -> None:
        @cross_validator(name="my_rule", description="Uma regra de exemplo.")
        def check(values: dict) -> str | None:  # type: ignore[type-arg]
            return "erro" if values.get("x") else None

        assert isinstance(check, CrossValidator)
        assert check.name == "my_rule"
        assert check.description == "Uma regra de exemplo."

    def test_decorated_validator_runs_correctly(self) -> None:
        @cross_validator(name="requires_bucket_when_s3_enabled")
        def check(values: dict) -> str | None:  # type: ignore[type-arg]
            if values.get("use_s3") and not values.get("aws_bucket"):
                return "AWS_BUCKET é obrigatório quando USE_S3=true."
            return None

        assert check.run({"use_s3": True, "aws_bucket": None}) is not None
        assert check.run({"use_s3": True, "aws_bucket": "my-bucket"}) is None
        assert check.run({"use_s3": False, "aws_bucket": None}) is None

    def test_decorator_default_description_is_empty(self) -> None:
        @cross_validator(name="my_rule")
        def check(values: dict) -> str | None:  # type: ignore[type-arg]
            return None

        assert check.description == ""
