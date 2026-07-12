"""CLI do config-validator, construída com Typer.

Fina por design: toda a lógica de negócio (compor fontes, validar,
formatar erros) já existe nas camadas de Application/Infrastructure —
este módulo só traduz argumentos de linha de comando em chamadas para
elas, e decide o que imprimir e qual exit code usar (RF09).

O Schema a documentar/validar é sempre definido pela aplicação que usa
esta biblioteca (não faz sentido a lib "adivinhar" o schema de outra
pessoa). Por isso, os comandos aceitam um caminho no formato
'modulo:atributo' — o mesmo padrão usado por ferramentas como
`uvicorn app:app` ou `gunicorn`.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

import typer

from config_validator.application.errors import ConfigValidationError
from config_validator.application.loader import Loader
from config_validator.application.validator import Validator
from config_validator.domain.field import Field, FieldKind
from config_validator.domain.schema import Schema

app = typer.Typer(
    help="config-validator: valide a configuração da sua aplicação antes do deploy."
)

def _schema_option() -> Any:
    """Fábrica do parâmetro --schema, comum a todos os comandos.

    IMPORTANTE: nunca compartilhe uma única instância de typer.Option(...)
    entre múltiplos comandos — o Typer/Click vincula metadados internos
    (nome do parâmetro, tipo resolvido) ao objeto no momento em que cada
    comando é construído. Reutilizar a mesma instância entre `check` e
    `docs` corrompe esse estado e quebra o parsing de argumentos de forma
    silenciosa e dependente de versão (bug real encontrado em CI, não
    reproduzido localmente antes do fix). Cada comando deve chamar esta
    função para obter sua PRÓPRIA instância.
    """
    return typer.Option(
        ...,
        "--schema",
        help="Caminho 'modulo:atributo' até o Schema (ex: 'myapp.config:schema').",
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
    schema: str = _schema_option(),
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


_KIND_LABELS: dict[FieldKind, str] = {
    FieldKind.STR: "string",
    FieldKind.INT: "inteiro",
    FieldKind.BOOL: "booleano",
    FieldKind.FLOAT: "decimal",
    FieldKind.LIST: "lista",
    FieldKind.ENUM: "enum",
    FieldKind.URL: "URL",
    FieldKind.PATH: "caminho de arquivo",
}


def _type_label(field: Field) -> str:
    """Rótulo legível do tipo de um campo, incluindo detalhes de LIST/ENUM."""
    if field.kind is FieldKind.ENUM and field.enum_class is not None:
        values = ", ".join(member.value for member in field.enum_class)
        return f"enum ({values})"
    if field.kind is FieldKind.LIST and field.item_kind is not None:
        item_label = _KIND_LABELS[field.item_kind]
        return f"lista de {item_label}"
    return _KIND_LABELS[field.kind]


def _default_repr(field: Field) -> Any:
    # Um default marcado como secret nunca deve ser exposto na documentação
    # gerada — mesmo aqui, onde o objetivo é justamente listar informação.
    if field.secret:
        return "**********"
    return field.default


def _field_to_dict(field: Field) -> dict[str, Any]:
    return {
        "name": field.name,
        "type": _type_label(field),
        "required": field.required,
        "default": None if field.required else _default_repr(field),
        "secret": field.secret,
        "description": field.description,
    }


def _default_for_env_example(field: Field) -> str:
    if field.required:
        return ""
    if field.secret:
        # Nunca ecoa um default secreto real num arquivo de template — mesmo
        # que o valor em si não seja sensível, o hábito de nunca expor
        # 'secret=True' em texto plano é o que evita vazamentos por engano.
        return "CHANGE_ME"
    default = field.default
    if default is None:
        return ""
    if isinstance(default, list):
        return ",".join(str(item) for item in default)
    return str(default)


def _env_example_lines(field: Field) -> list[str]:
    obligation = "Obrigatório" if field.required else "Opcional"
    comment_parts = [obligation, f"tipo: {_type_label(field)}"]
    if field.description:
        comment_parts.append(field.description)
    comment = " — ".join(comment_parts)

    value = _default_for_env_example(field)
    return [f"# {comment}", f"{field.name}={value}"]


def _print_env_example(schema: Schema) -> None:
    lines: list[str] = [
        "# Gerado por 'config-validator docs --format env'.",
        "# Ajuste os valores conforme o seu ambiente antes de usar.",
        "",
    ]
    for field in schema:
        lines.extend(_env_example_lines(field))
        lines.append("")

    typer.echo("\n".join(lines).rstrip())


@app.command()
def docs(
    schema: str = _schema_option(),
    output_format: str = typer.Option(
        "table", "--format", help="Formato de saída: 'table' (padrão), 'json' ou 'env'."
    ),
) -> None:
    """Lista todos os campos de configuração esperados pelo Schema (RF06).

    Útil para onboarding de novos desenvolvedores e para gerar
    documentação automática do que a aplicação espera encontrar no
    ambiente, sem precisar ler o código-fonte do Schema. O formato 'env'
    gera um `.env.example` pronto para redirecionar para um arquivo.
    """
    schema_obj = _import_schema(schema)

    if output_format not in {"table", "json", "env"}:
        raise typer.BadParameter(
            f"Formato {output_format!r} desconhecido. Use 'table', 'json' ou 'env'."
        )

    if output_format == "env":
        _print_env_example(schema_obj)
        return

    fields_data = [_field_to_dict(field) for field in schema_obj]

    if output_format == "json":
        typer.echo(json.dumps(fields_data, indent=2, ensure_ascii=False))
        return

    _print_table(fields_data)


def _print_table(fields_data: list[dict[str, Any]]) -> None:
    if not fields_data:
        typer.echo("Este Schema não possui nenhum campo definido.")
        return

    headers = ("NOME", "TIPO", "OBRIGATÓRIO", "DEFAULT", "DESCRIÇÃO")
    rows = [
        (
            str(field["name"]),
            str(field["type"]),
            "sim" if field["required"] else "não",
            "-" if field["required"] else str(field["default"]),
            str(field["description"]) or "-",
        )
        for field in fields_data
    ]

    widths = [
        max(len(header), *(len(row[i]) for row in rows)) for i, header in enumerate(headers)
    ]

    def _format_row(row: tuple[str, ...]) -> str:
        return "  ".join(cell.ljust(width) for cell, width in zip(row, widths, strict=True))

    typer.echo(_format_row(headers))
    typer.echo(_format_row(tuple("-" * width for width in widths)))
    for row in rows:
        typer.echo(_format_row(row))


if __name__ == "__main__":  # pragma: no cover
    app()
