"""Testes unitários para config_validator.application.error_formatter.

Testa a função de formatação diretamente com erros sintéticos (no formato
que pydantic.ValidationError.errors() produz), sem precisar disparar um
ValidationError real do Pydantic para cada tipo de erro — isso permite
cobrir facilmente casos de borda como um tipo de erro não mapeado.
"""

from config_validator.application.error_formatter import format_pydantic_errors
from config_validator.domain.field import Field, FieldKind
from config_validator.domain.schema import Schema


class TestFormatPydanticErrors:
    def test_missing_field_error(self) -> None:
        schema = Schema.of(Field(name="database_url", kind=FieldKind.STR))
        errors = [{"loc": ("database_url",), "type": "missing", "msg": "Field required"}]

        result = format_pydantic_errors(errors, schema)

        assert "obrigatório" in result[0]

    def test_error_for_field_not_present_in_schema_does_not_crash(self) -> None:
        # Caso de borda: o loc do erro do Pydantic referencia um nome que
        # não existe no Schema (não deveria acontecer em uso normal, já que
        # o modelo é construído a partir do próprio Schema, mas o formatter
        # não deve quebrar se acontecer — só não inclui a descrição extra).
        schema = Schema.of(Field(name="database_url", kind=FieldKind.STR))
        errors = [{"loc": ("campo_inexistente",), "type": "missing", "msg": "Field required"}]

        result = format_pydantic_errors(errors, schema)

        assert "'campo_inexistente'" in result[0]

    def test_unmapped_error_type_falls_back_to_pydantic_message(self) -> None:
        schema = Schema.of(Field(name="webhook_url", kind=FieldKind.URL))
        errors = [
            {
                "loc": ("webhook_url",),
                "type": "some_future_pydantic_error_type",
                "msg": "Some new kind of error Pydantic added later",
            }
        ]

        result = format_pydantic_errors(errors, schema)

        assert result[0] == "'webhook_url': Some new kind of error Pydantic added later."

    def test_fallback_does_not_duplicate_punctuation(self) -> None:
        # Bug real encontrado durante o desenvolvimento: se a mensagem do
        # Pydantic já termina em ponto, não devemos acrescentar um segundo.
        schema = Schema.of(Field(name="webhook_url", kind=FieldKind.URL))
        errors = [
            {
                "loc": ("webhook_url",),
                "type": "some_future_pydantic_error_type",
                "msg": "Message that already ends with a period.",
            }
        ]

        result = format_pydantic_errors(errors, schema)

        assert result[0] == "'webhook_url': Message that already ends with a period."
        assert ".." not in result[0]

    def test_description_appended_when_available(self) -> None:
        schema = Schema.of(
            Field(name="port", kind=FieldKind.INT, description="Porta HTTP do servidor.")
        )
        errors = [{"loc": ("port",), "type": "int_parsing", "msg": "..."}]

        result = format_pydantic_errors(errors, schema)

        assert "Porta HTTP do servidor." in result[0]

    def test_no_description_means_no_parentheses_suffix(self) -> None:
        schema = Schema.of(Field(name="port", kind=FieldKind.INT))
        errors = [{"loc": ("port",), "type": "int_parsing", "msg": "..."}]

        result = format_pydantic_errors(errors, schema)

        assert result[0] == "'port' recebeu um valor que não é um número inteiro válido."
