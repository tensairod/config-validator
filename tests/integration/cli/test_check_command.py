"""Testes de integração do comando `config-validator check`, ponta a ponta.

Usam typer.testing.CliRunner (invoca o comando de verdade, sem mockar
nada), com um arquivo .env real em tmp_path e um módulo de Schema real
inserido no sys.path — o mesmo caminho que um usuário real da lib
percorreria ao rodar `config-validator check --schema myapp.config:schema`
no seu próprio projeto.
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from config_validator.cli.main import app

runner = CliRunner()

_SCHEMA_MODULE = """
from config_validator.domain.field import Field, FieldKind
from config_validator.domain.schema import Schema

schema = Schema.of(
    Field(name="database_url", kind=FieldKind.STR),
    Field(name="port", kind=FieldKind.INT),
)
"""


@pytest.fixture
def schema_module(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Cria um módulo de Schema real em tmp_path e o disponibiliza via sys.path.

    Retorna o caminho 'modulo:atributo' pronto para passar em --schema.
    """
    (tmp_path / "integration_test_app_config.py").write_text(_SCHEMA_MODULE)
    monkeypatch.syspath_prepend(str(tmp_path))
    return "integration_test_app_config:schema"


class TestCheckCommandSuccess:
    def test_valid_config_exits_zero(self, tmp_path: Path, schema_module: str) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("database_url=postgres://localhost\nport=5432\n")

        result = runner.invoke(
            app, ["--schema", schema_module, "--env-file", str(env_file)]
        )

        assert result.exit_code == 0
        assert "Configuração válida" in result.stdout

    def test_profile_file_is_used_with_precedence(self, tmp_path: Path, schema_module: str) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("database_url=from_base\nport=1\n")
        profile_file = tmp_path / ".env.production"
        profile_file.write_text("database_url=from_production\n")

        result = runner.invoke(
            app,
            [
                "--schema",
                schema_module,
                "--env-file",
                str(env_file),
                "--profile",
                "production",
            ],
        )

        assert result.exit_code == 0


class TestCheckCommandFailure:
    def test_missing_required_field_exits_one(self, tmp_path: Path, schema_module: str) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("port=5432\n")  # database_url ausente

        result = runner.invoke(
            app, ["--schema", schema_module, "--env-file", str(env_file)]
        )

        assert result.exit_code == 1
        assert "Configuração inválida" in result.stdout
        assert "database_url" in result.stdout

    def test_invalid_type_exits_one(self, tmp_path: Path, schema_module: str) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("database_url=postgres://localhost\nport=not-a-number\n")

        result = runner.invoke(
            app, ["--schema", schema_module, "--env-file", str(env_file)]
        )

        assert result.exit_code == 1
        assert "número inteiro válido" in result.stdout

    def test_invalid_schema_path_format_exits_nonzero(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("")

        result = runner.invoke(
            app, ["--schema", "formato_invalido_sem_dois_pontos", "--env-file", str(env_file)]
        )

        assert result.exit_code != 0

    def test_nonexistent_schema_module_exits_nonzero(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("")

        result = runner.invoke(
            app,
            ["--schema", "modulo_inexistente_xyz:schema", "--env-file", str(env_file)],
        )

        assert result.exit_code != 0
