"""Testes para config_validator.infrastructure.env_var_source.EnvVarSource."""

from config_validator.infrastructure.env_var_source import EnvVarSource


class TestEnvVarSource:
    def test_loads_values_from_injected_environ(self) -> None:
        fake_environ = {"DATABASE_URL": "postgres://localhost", "DEBUG": "false"}
        source = EnvVarSource(environ=fake_environ)
        assert source.load() == fake_environ

    def test_returns_a_copy_not_the_original_mapping(self) -> None:
        # Garante que mutar o resultado de load() não afeta o ambiente original —
        # importante porque o Merger (Loader) vai combinar dicts de várias fontes,
        # e não queremos efeitos colaterais entre chamadas.
        fake_environ = {"KEY": "value"}
        source = EnvVarSource(environ=fake_environ)
        result = source.load()
        result["KEY"] = "mutated"
        assert fake_environ["KEY"] == "value"

    def test_empty_environ_returns_empty_dict(self) -> None:
        source = EnvVarSource(environ={})
        assert source.load() == {}

    def test_default_constructor_reads_real_os_environ(self) -> None:
        import os

        os.environ["CONFIG_VALIDATOR_TEST_VAR"] = "test-value"
        try:
            source = EnvVarSource()
            assert source.load()["CONFIG_VALIDATOR_TEST_VAR"] == "test-value"
        finally:
            del os.environ["CONFIG_VALIDATOR_TEST_VAR"]
