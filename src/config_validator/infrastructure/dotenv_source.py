"""Fonte de configuração que lê um arquivo .env específico.

Escopo deliberadamente restrito: esta classe só sabe ler UM arquivo, no
caminho que foi passado a ela. Ela não decide qual arquivo ler baseado em
perfil (development/staging/production), nem resolve precedência frente
a outras fontes — essas responsabilidades pertencem ao Loader (Issue
#6.5), que vai compor múltiplas instâncias de ConfigSource (incluindo
mais de um DotEnvSource, um por perfil, se for o caso).
"""

from __future__ import annotations

from pathlib import Path

from dotenv import dotenv_values


class DotEnvSource:
    """Implementação de ConfigSource que lê um arquivo `.env`.

    Args:
        path: caminho do arquivo a ser lido. Default: `.env` no
            diretório de trabalho atual.
    """

    def __init__(self, path: str | Path = ".env") -> None:
        self._path = Path(path)

    def load(self) -> dict[str, str]:
        """Lê o arquivo .env configurado.

        Se o arquivo não existir, retorna um dict vazio — a ausência de
        um arquivo .env opcional não é um erro (muitos ambientes de
        produção não usam .env, só variáveis de ambiente reais).
        """
        if not self._path.exists():
            return {}

        # dotenv_values retorna dict[str, str | None]: uma linha como
        # `FOO` (sem `=valor`) vira `{"FOO": None}`. Filtramos esses casos
        # fora — um valor ausente em um .env não deve virar a string "None".
        raw_values = dotenv_values(self._path)
        return {key: value for key, value in raw_values.items() if value is not None}
