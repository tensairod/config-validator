"""Exceção agregando todas as violações de validação encontradas (ADR-004).

Nunca é levantada na primeira violação encontrada — o Validator sempre
coleta todos os erros de todos os campos (e, se a validação de campo
passou integralmente, também todas as violações de regras cruzadas)
antes de levantar esta exceção uma única vez.
"""

from __future__ import annotations


class ConfigValidationError(Exception):
    """Levantada quando um ou mais campos/regras de configuração são inválidos.

    Args:
        errors: lista de mensagens de erro acionáveis, uma por violação
            encontrada (RNF07 — cada mensagem já diz o que corrigir, não
            só o que está errado).
    """

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        formatted = "\n".join(f"  - {error}" for error in errors)
        super().__init__(f"Configuração inválida ({len(errors)} erro(s)):\n{formatted}")
