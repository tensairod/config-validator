"""Testes unitários para config_validator.domain.secret.SecretValue."""

import pytest

from config_validator.domain.secret import SecretValue


class TestSecretValueMasking:
    def test_repr_masks_content(self) -> None:
        secret = SecretValue("super-secret-api-key")
        assert "super-secret-api-key" not in repr(secret)
        assert repr(secret) == "SecretValue('**********')"

    def test_str_masks_content(self) -> None:
        secret = SecretValue("super-secret-api-key")
        assert "super-secret-api-key" not in str(secret)
        assert str(secret) == "**********"

    def test_fstring_masks_content(self) -> None:
        secret = SecretValue("super-secret-api-key")
        rendered = f"api_key={secret}"
        assert "super-secret-api-key" not in rendered
        assert rendered == "api_key=**********"

    def test_masking_holds_inside_a_container(self) -> None:
        # O caso real que motiva esta classe: alguém faz `print(config_dict)`
        # e o segredo não pode vazar mesmo estando dentro de outra estrutura.
        secret = SecretValue("super-secret-api-key")
        container = {"api_key": secret, "debug": True}
        assert "super-secret-api-key" not in repr(container)
        assert "super-secret-api-key" not in str(container)


class TestSecretValueReveal:
    def test_reveal_returns_real_value(self) -> None:
        secret = SecretValue("super-secret-api-key")
        assert secret.reveal() == "super-secret-api-key"

    def test_reveal_works_for_non_string_values(self) -> None:
        secret = SecretValue(12345)
        assert secret.reveal() == 12345


class TestSecretValueEquality:
    def test_equal_when_underlying_value_matches(self) -> None:
        assert SecretValue("x") == SecretValue("x")

    def test_not_equal_when_underlying_value_differs(self) -> None:
        assert SecretValue("x") != SecretValue("y")

    def test_not_equal_to_raw_value(self) -> None:
        # Comparar direto com o valor cru não deve "vazar" através de ==;
        # força o uso explícito de .reveal() para comparar.
        assert SecretValue("x") != "x"

    def test_not_hashable(self) -> None:
        with pytest.raises(TypeError):
            hash(SecretValue("x"))
