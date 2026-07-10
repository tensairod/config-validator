"""Testes unitários para config_validator.application.loader.Loader.

Usam fontes fake (sem I/O real) para testar isoladamente a lógica de
merge/precedência. Os testes da composição real de fontes (arquivos .env
+ variáveis de ambiente) estão em tests/integration/application/.
"""

from config_validator.application.loader import Loader


class _FakeSource:
    """ConfigSource fake para testar o Loader sem depender de I/O real."""

    def __init__(self, values: dict[str, str]) -> None:
        self._values = values

    def load(self) -> dict[str, str]:
        return dict(self._values)


class TestLoaderMerge:
    def test_single_source(self) -> None:
        loader = Loader(sources=(_FakeSource({"a": "1"}),))
        assert loader.load() == {"a": "1"}

    def test_later_source_wins_on_conflict(self) -> None:
        low_precedence = _FakeSource({"a": "low", "b": "only_low"})
        high_precedence = _FakeSource({"a": "high"})
        loader = Loader(sources=(low_precedence, high_precedence))

        assert loader.load() == {"a": "high", "b": "only_low"}

    def test_empty_sources_returns_empty_dict(self) -> None:
        loader = Loader(sources=())
        assert loader.load() == {}

    def test_three_sources_precedence_chain(self) -> None:
        s1 = _FakeSource({"a": "from_s1", "b": "from_s1"})
        s2 = _FakeSource({"a": "from_s2"})
        s3 = _FakeSource({"c": "from_s3"})
        loader = Loader(sources=(s1, s2, s3))

        assert loader.load() == {"a": "from_s2", "b": "from_s1", "c": "from_s3"}

    def test_source_with_no_overlapping_keys(self) -> None:
        s1 = _FakeSource({"a": "1"})
        s2 = _FakeSource({"b": "2"})
        loader = Loader(sources=(s1, s2))

        assert loader.load() == {"a": "1", "b": "2"}
