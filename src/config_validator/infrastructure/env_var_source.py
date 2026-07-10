"""Fonte de configuração que lê variáveis de ambiente reais do processo."""

from __future__ import annotations

import os
from collections.abc import MutableMapping


class EnvVarSource:
    """Implementação de ConfigSource que lê `os.environ`.

    Aceita um `environ` customizado via injeção de dependência — isso
    existe para que os testes não precisem usar `monkeypatch.setenv` (que
    muta o ambiente real do processo de teste, ainda que temporariamente).
    Em produção, basta usar `EnvVarSource()` sem argumentos.
    """

    def __init__(self, environ: MutableMapping[str, str] | None = None) -> None:
        self._environ: MutableMapping[str, str] = environ if environ is not None else os.environ

    def load(self) -> dict[str, str]:
        return dict(self._environ)
