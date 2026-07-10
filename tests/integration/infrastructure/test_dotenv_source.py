"""Testes de integração para DotEnvSource.

Vivem em tests/integration/ (não unit/) porque tocam o filesystem real
via tmp_path do pytest — não são mocks, são arquivos .env de verdade
sendo escritos e lidos em um diretório temporário isolado.
"""

from pathlib import Path

import pytest

from config_validator.infrastructure.dotenv_source import DotEnvSource


class TestDotEnvSource:
    def test_loads_values_from_existing_file(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("DATABASE_URL=postgres://localhost\nDEBUG=false\n")

        source = DotEnvSource(path=env_file)

        assert source.load() == {"DATABASE_URL": "postgres://localhost", "DEBUG": "false"}

    def test_missing_file_returns_empty_dict(self, tmp_path: Path) -> None:
        source = DotEnvSource(path=tmp_path / "does_not_exist.env")
        assert source.load() == {}

    def test_key_without_value_is_filtered_out(self, tmp_path: Path) -> None:
        # Uma linha "CHAVE" sem "=valor" é válida em sintaxe .env, mas
        # dotenv_values devolve None para ela — não deve virar a string "None".
        env_file = tmp_path / ".env"
        env_file.write_text("CHAVE_SEM_VALOR\nOUTRA=presente\n")

        source = DotEnvSource(path=env_file)

        assert source.load() == {"OUTRA": "presente"}

    def test_empty_file_returns_empty_dict(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("")

        source = DotEnvSource(path=env_file)

        assert source.load() == {}

    def test_default_path_reads_dot_env_from_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=from_cwd\n")
        monkeypatch.chdir(tmp_path)

        source = DotEnvSource()

        assert source.load() == {"KEY": "from_cwd"}

    def test_accepts_string_path_as_well_as_path_object(self, tmp_path: Path) -> None:
        env_file = tmp_path / "custom.env"
        env_file.write_text("KEY=value\n")

        source = DotEnvSource(path=str(env_file))

        assert source.load() == {"KEY": "value"}
