"""Testes para config_validator.application.config_source.ConfigSource.

Como ConfigSource é um Protocol, não há muito o que testar isoladamente
além de confirmar que a checagem estrutural (`isinstance` com Protocol
runtime_checkable) funciona como esperado — isso serve de documentação
executável do contrato.
"""

from config_validator.application.config_source import ConfigSource


class _FakeSource:
    """Objeto que satisfaz o Protocol sem herdar de nada."""

    def load(self) -> dict[str, str]:
        return {"foo": "bar"}


class _NotASource:
    """Objeto que claramente não satisfaz o Protocol."""


class TestConfigSourceProtocol:
    def test_object_with_matching_load_method_satisfies_protocol(self) -> None:
        assert isinstance(_FakeSource(), ConfigSource)

    def test_object_without_load_method_does_not_satisfy_protocol(self) -> None:
        assert not isinstance(_NotASource(), ConfigSource)
