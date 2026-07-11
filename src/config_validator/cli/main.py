"""CLI do config-validator, construída com Typer.

Fina por design: toda a lógica de negócio (compor fontes, validar,
formatar erros) já existe nas camadas de Application/Infrastructure —
este módulo só traduz argumentos de linha de comando em chamadas para
elas, e decide o que imprimir e qual exit code usar (RF09).

O Schema a validar é sempre definido pela aplicação que usa esta
biblioteca (não faz sentido a lib "adivinhar" o schema de outra pessoa).
Por isso, o comando aceita um caminho no formato 'modulo:atributo' — o
mesmo padrão usado por ferramentas como `uvicorn app:app` ou `gunicorn`.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import typer

from config_validator.application.errors import ConfigValidationError
from config_validator.application.loader import Loader
from config_validator.application.validator import Validator
from config_validator.domain.schema import Schema

app = typer.Typer(
    help="config-validator: valide a configuração da sua aplicação antes do deploy."
)


def _import_schema(schema_path: str) -> Schema:
    """Importa um Schema a partir de uma string 'modulo:atributo'.

    Exemplo: 'myapp.config:schema' importa o módulo 'myapp.config' e
    devolve o atributo 'schema' definido nele.

    Raises:
        typer.BadParameter: se o formato for inválido, o módulo não puder
            ser importado, o atributo não existir, ou o atributo não for
            uma instância de Schema. Usar BadParameter (em vez de deixar
            a exceção original propagar) garante uma mensagem de erro
            amigável e um exit code apropriado de erro de uso da CLI.
    """
    if ":" not in schema_path:
        raise typer.BadParameter(
            f"Formato inválido: {schema_path!r}. Use 'modulo.py_path:nome_da_variavel' "
            "(ex: 'myapp.config:schema')."
        )

    module_name, attribute_name = schema_path.split(":", 1)

    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise typer.BadParameter(
            f"Não foi possível importar o módulo {module_name!r}: {exc}"
        ) from exc

    try:
        schema = getattr(module, attribute_name)
    except AttributeError as exc:
        raise typer.BadParameter(
            f"O módulo {module_name!r} não possui um atributo chamado {attribute_name!r}."
        ) from exc

    if not isinstance(schema, Schema):
        raise typer.BadParameter(
            f"{schema_path!r} não é uma instância de Schema "
            f"(encontrado: {type(schema).__name__})."
        )

    return schema


@app.command()
def check(
    schema: str = typer.Option(
        ...,
        "--schema",
        help="Caminho 'modulo:atributo' até o Schema a validar (ex: 'myapp.config:schema').",
    ),
    env_file: Path = typer.Option(
        Path(".env"), "--env-file", help="Caminho do arquivo .env base."
    ),
    profile: str | None = typer.Option(
        None,
        "--profile",
        help=(
            "Perfil de ambiente (ex: 'production'). Se informado, "
            "'.env.{profile}' é lido com precedência sobre --env-file."
        ),
    ),
) -> None:
    """Valida a configuração sem subir a aplicação.

    Pensado para uso em pipelines de CI/CD antes do deploy: exit code 0
    se a configuração for válida, 1 se houver qualquer erro.
    """
    schema_obj = _import_schema(schema)
    loader = Loader.with_default_sources(profile=profile, base_path=env_file)
    raw_values = loader.load()

    try:
        Validator().validate(schema_obj, raw_values)
    except ConfigValidationError as exc:
        typer.secho("Configuração inválida:", fg=typer.colors.RED, bold=True)
        for error in exc.errors:
            typer.secho(f"  - {error}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from None

    typer.secho("Configuração válida.", fg=typer.colors.GREEN, bold=True)
    raise typer.Exit(code=0)


if __name__ == "__main__":  # pragma: no cover
    app()
