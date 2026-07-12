"""Testes de integração do comando `config-validator docs`, ponta a ponta."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from config_validator.cli.main import app

runner = CliRunner()

_SCHEMA_MODULE = """
from enum import Enum
from config_validator.domain.field import Field, FieldKind
from config_validator.domain.schema import Schema


class Environment(Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"


schema = Schema.of(
    Field(
        name="database_url",
        kind=FieldKind.STR,
        description="URL de conexao com o PostgreSQL.",
    ),
    Field(name="debug", kind=FieldKind.BOOL, required=False, default=False),
    Field(name="api_key", kind=FieldKind.STR, required=False, default="fallback-key", secret=True),
    Field(name="env", kind=FieldKind.ENUM, enum_class=Environment),
    Field(name="allowed_hosts", kind=FieldKind.LIST, required=False, default=[]),
)

empty_schema = Schema.of()
"""


@pytest.fixture
def docs_schema_module(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    (tmp_path / "docs_test_app_config.py").write_text(_SCHEMA_MODULE)
    monkeypatch.syspath_prepend(str(tmp_path))
    return "docs_test_app_config:schema"


class TestDocsCommandTableFormat:
    def test_lists_all_fields_by_default(self, docs_schema_module: str) -> None:
        result = runner.invoke(app, ["docs", "--schema", docs_schema_module])

        assert result.exit_code == 0
        assert "database_url" in result.stdout
        assert "debug" in result.stdout
        assert "api_key" in result.stdout

    def test_enum_field_shows_accepted_values(self, docs_schema_module: str) -> None:
        result = runner.invoke(app, ["docs", "--schema", docs_schema_module])

        lines = result.stdout.splitlines()
        env_line = next(line for line in lines if line.strip().startswith("env "))
        assert "enum (development, production)" in env_line

    def test_list_field_shows_item_type(self, docs_schema_module: str) -> None:
        result = runner.invoke(app, ["docs", "--schema", docs_schema_module])

        lines = result.stdout.splitlines()
        list_line = next(line for line in lines if "allowed_hosts" in line)
        assert "lista de string" in list_line

    def test_required_field_marked_as_sim(self, docs_schema_module: str) -> None:
        result = runner.invoke(app, ["docs", "--schema", docs_schema_module])

        lines = result.stdout.splitlines()
        database_url_line = next(line for line in lines if "database_url" in line)
        assert "sim" in database_url_line

    def test_optional_field_marked_as_nao(self, docs_schema_module: str) -> None:
        result = runner.invoke(app, ["docs", "--schema", docs_schema_module])

        lines = result.stdout.splitlines()
        debug_line = next(line for line in lines if line.strip().startswith("debug"))
        assert "não" in debug_line

    def test_description_appears_in_table(self, docs_schema_module: str) -> None:
        result = runner.invoke(app, ["docs", "--schema", docs_schema_module])

        assert "URL de conexao com o PostgreSQL." in result.stdout

    def test_secret_default_is_masked_in_table(self, docs_schema_module: str) -> None:
        result = runner.invoke(app, ["docs", "--schema", docs_schema_module])

        assert "fallback-key" not in result.stdout
        assert "**********" in result.stdout

    def test_empty_schema_prints_friendly_message(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "empty_config.py").write_text(_SCHEMA_MODULE)
        monkeypatch.syspath_prepend(str(tmp_path))

        result = runner.invoke(app, ["docs", "--schema", "empty_config:empty_schema"])

        assert result.exit_code == 0
        assert "não possui nenhum campo" in result.stdout


class TestDocsCommandJsonFormat:
    def test_json_format_is_valid_and_complete(self, docs_schema_module: str) -> None:
        import json

        result = runner.invoke(app, ["docs", "--schema", docs_schema_module, "--format", "json"])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data) == 5
        names = {item["name"] for item in data}
        assert names == {"database_url", "debug", "api_key", "env", "allowed_hosts"}

    def test_json_masks_secret_default_too(self, docs_schema_module: str) -> None:
        import json

        result = runner.invoke(app, ["docs", "--schema", docs_schema_module, "--format", "json"])

        data = json.loads(result.stdout)
        api_key_entry = next(item for item in data if item["name"] == "api_key")
        assert api_key_entry["default"] == "**********"
        assert api_key_entry["secret"] is True

    def test_json_required_field_has_null_default(self, docs_schema_module: str) -> None:
        import json

        result = runner.invoke(app, ["docs", "--schema", docs_schema_module, "--format", "json"])

        data = json.loads(result.stdout)
        database_url_entry = next(item for item in data if item["name"] == "database_url")
        assert database_url_entry["default"] is None
        assert database_url_entry["required"] is True


class TestDocsCommandEnvFormat:
    def test_env_format_includes_all_field_names(self, docs_schema_module: str) -> None:
        result = runner.invoke(app, ["docs", "--schema", docs_schema_module, "--format", "env"])

        assert result.exit_code == 0
        assert "database_url=" in result.stdout
        assert "debug=" in result.stdout
        assert "api_key=" in result.stdout
        assert "env=" in result.stdout
        assert "allowed_hosts=" in result.stdout

    def test_env_format_required_field_has_no_value(self, docs_schema_module: str) -> None:
        result = runner.invoke(app, ["docs", "--schema", docs_schema_module, "--format", "env"])

        lines = result.stdout.splitlines()
        database_url_line = next(line for line in lines if line.startswith("database_url="))
        assert database_url_line == "database_url="

    def test_env_format_optional_non_secret_field_shows_real_default(
        self, docs_schema_module: str
    ) -> None:
        result = runner.invoke(app, ["docs", "--schema", docs_schema_module, "--format", "env"])

        lines = result.stdout.splitlines()
        debug_line = next(line for line in lines if line.startswith("debug="))
        assert debug_line == "debug=False"

    def test_env_format_secret_field_never_shows_real_default(
        self, docs_schema_module: str
    ) -> None:
        result = runner.invoke(app, ["docs", "--schema", docs_schema_module, "--format", "env"])

        assert "fallback-key" not in result.stdout
        lines = result.stdout.splitlines()
        api_key_line = next(line for line in lines if line.startswith("api_key="))
        assert api_key_line == "api_key=CHANGE_ME"

    def test_env_format_list_default_joined_by_comma(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        module = """
from config_validator.domain.field import Field, FieldKind
from config_validator.domain.schema import Schema

schema = Schema.of(
    Field(
        name="allowed_hosts",
        kind=FieldKind.LIST,
        required=False,
        default=["a.com", "b.com"],
    )
)
"""
        (tmp_path / "list_default_config.py").write_text(module)
        monkeypatch.syspath_prepend(str(tmp_path))

        result = runner.invoke(
            app,
            ["docs", "--schema", "list_default_config:schema", "--format", "env"],
        )

        assert "allowed_hosts=a.com,b.com" in result.stdout

    def test_env_format_none_default_renders_as_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        module = """
from config_validator.domain.field import Field, FieldKind
from config_validator.domain.schema import Schema

schema = Schema.of(
    Field(name="proxy_url", kind=FieldKind.STR, required=False, default=None)
)
"""
        (tmp_path / "none_default_config.py").write_text(module)
        monkeypatch.syspath_prepend(str(tmp_path))

        result = runner.invoke(
            app,
            ["docs", "--schema", "none_default_config:schema", "--format", "env"],
        )

        lines = result.stdout.splitlines()
        proxy_url_line = next(line for line in lines if line.startswith("proxy_url="))
        assert proxy_url_line == "proxy_url="

    def test_env_format_has_header_comment(self, docs_schema_module: str) -> None:
        result = runner.invoke(app, ["docs", "--schema", docs_schema_module, "--format", "env"])

        assert "Gerado por 'config-validator docs --format env'" in result.stdout

    def test_env_format_output_is_redirectable_to_a_file(
        self, docs_schema_module: str, tmp_path: Path
    ) -> None:
        # Simula o uso real: `config-validator docs --format env > .env.example`
        result = runner.invoke(app, ["docs", "--schema", docs_schema_module, "--format", "env"])
        output_file = tmp_path / ".env.example"
        output_file.write_text(result.stdout)

        assert "database_url=" in output_file.read_text()


class TestDocsCommandErrors:
    def test_unknown_format_raises_bad_parameter(self, docs_schema_module: str) -> None:
        result = runner.invoke(
            app, ["docs", "--schema", docs_schema_module, "--format", "xml"]
        )

        assert result.exit_code != 0
