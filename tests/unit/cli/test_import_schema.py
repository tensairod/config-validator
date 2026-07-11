"""Testes unitários para config_validator.cli.main._import_schema.

Cria arquivos .py reais em um diretório temporário e os insere no
sys.path via monkeypatch.syspath_prepend — isso testa a importação
dinâmica de verdade (não um mock de importlib), do mesmo jeito que
aconteceria com o schema de uma aplicação real do usuário da lib.
"""

from pathlib import Path

import pytest
import typer

from config_validator.cli.main import _import_schema
from config_validator.domain.schema import Schema

_VALID_SCHEMA_MODULE = """
from config_validator.domain.field import Field, FieldKind
from config_validator.domain.schema import Schema

schema = Schema.of(Field(name="database_url", kind=FieldKind.STR))
not_a_schema = "just a string"
"""


def _write_module(tmp_path: Path, filename: str, content: str) -> None:
    (tmp_path / filename).write_text(content)


class TestImportSchema:
    def test_imports_valid_schema_successfully(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_module(tmp_path, "valid_app_config_1.py", _VALID_SCHEMA_MODULE)
        monkeypatch.syspath_prepend(str(tmp_path))

        result = _import_schema("valid_app_config_1:schema")

        assert isinstance(result, Schema)
        assert len(result) == 1

    def test_missing_colon_raises_bad_parameter(self) -> None:
        with pytest.raises(typer.BadParameter, match="Formato inválido"):
            _import_schema("modulo_sem_dois_pontos")

    def test_module_not_found_raises_bad_parameter(self) -> None:
        with pytest.raises(typer.BadParameter, match="Não foi possível importar"):
            _import_schema("modulo_que_nao_existe_de_verdade:schema")

    def test_attribute_not_found_raises_bad_parameter(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_module(tmp_path, "valid_app_config_2.py", _VALID_SCHEMA_MODULE)
        monkeypatch.syspath_prepend(str(tmp_path))

        with pytest.raises(typer.BadParameter, match="não possui um atributo"):
            _import_schema("valid_app_config_2:atributo_que_nao_existe")

    def test_attribute_not_a_schema_raises_bad_parameter(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_module(tmp_path, "valid_app_config_3.py", _VALID_SCHEMA_MODULE)
        monkeypatch.syspath_prepend(str(tmp_path))

        with pytest.raises(typer.BadParameter, match="não é uma instância de Schema"):
            _import_schema("valid_app_config_3:not_a_schema")
