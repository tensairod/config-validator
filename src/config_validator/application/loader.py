"""Compõe múltiplas ConfigSource e resolve precedência entre elas (RF01, RF08).

Ordem de precedência ao usar `with_default_sources` (do mais baixo para o
mais alto):
1. Arquivo `.env` base
2. Arquivo de perfil específico (`.env.{profile}`), se um profile for informado
3. Variáveis de ambiente reais

Um valor presente em uma fonte de maior precedência sempre sobrescreve o
mesmo valor vindo de uma fonte de menor precedência. Note que o Loader só
sabe fazer merge de dicts brutos (str -> str) — ele não conhece Schema
nem Field. Decidir "o que fazer se um campo obrigatório não aparecer em
nenhuma fonte" é responsabilidade do Validator (M3), não do Loader.
"""

from __future__ import annotations

from collections.abc import MutableMapping
from pathlib import Path

from config_validator.application.config_source import ConfigSource
from config_validator.infrastructure.dotenv_source import DotEnvSource
from config_validator.infrastructure.env_var_source import EnvVarSource


class Loader:
    """Orquestra a leitura e o merge de múltiplas ConfigSource.

    Args:
        sources: fontes em ORDEM CRESCENTE de precedência — a última da
            lista vence em caso de conflito. Essa convenção espelha como
            merge de dicts funciona naturalmente em Python
            (`{**a, **b}`, onde b vence), evitando inventar uma API
            própria de "prioridade" numérica.
    """

    def __init__(self, sources: tuple[ConfigSource, ...]) -> None:
        self._sources = sources

    def load(self) -> dict[str, str]:
        """Executa o merge de todas as fontes, na ordem de precedência definida."""
        merged: dict[str, str] = {}
        for source in self._sources:
            merged.update(source.load())
        return merged

    @classmethod
    def with_default_sources(
        cls,
        profile: str | None = None,
        base_path: str | Path = ".env",
        environ: MutableMapping[str, str] | None = None,
    ) -> Loader:
        """Atalho de conveniência com a composição padrão de fontes (RF01, RF08):
        `.env` base -> `.env.{profile}` (se informado) -> variáveis de ambiente reais.

        Args:
            profile: nome do perfil (ex: "production"). Se informado, o
                arquivo `.env.{profile}` é lido e tem precedência sobre o
                `.env` base — mas ainda perde para variáveis de ambiente
                reais. Se o arquivo de perfil não existir, é silenciosamente
                ignorado (mesma semântica de "arquivo .env ausente" do
                DotEnvSource).
            base_path: caminho do arquivo `.env` base.
            environ: mapping de variáveis de ambiente a usar em vez de
                `os.environ` real — existe para permitir testes de
                integração sem tocar no ambiente real do processo (mesma
                razão de design do parâmetro equivalente em EnvVarSource).
        """
        base_path = Path(base_path)
        sources: list[ConfigSource] = [DotEnvSource(path=base_path)]

        if profile is not None:
            profile_path = base_path.with_name(f"{base_path.name}.{profile}")
            sources.append(DotEnvSource(path=profile_path))

        sources.append(EnvVarSource(environ=environ))
        return cls(sources=tuple(sources))
