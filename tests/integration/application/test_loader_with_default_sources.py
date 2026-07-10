"""Testes de integração para Loader.with_default_sources — a composição
real de DotEnvSource + EnvVarSource com precedência (RF01, RF08).

Usam tmp_path (arquivos .env reais em disco) e um `environ` injetado
(em vez de monkeypatch.setenv) para manter os testes rápidos e isolados
do ambiente real do processo, mesma razão de design documentada em
EnvVarSource.
"""

from pathlib import Path

from config_validator.application.loader import Loader


class TestLoaderWithDefaultSources:
    def test_base_env_file_only(self, tmp_path: Path) -> None:
        base = tmp_path / ".env"
        base.write_text("DATABASE_URL=from_base\n")

        loader = Loader.with_default_sources(base_path=base, environ={})

        assert loader.load() == {"DATABASE_URL": "from_base"}

    def test_profile_file_overrides_base(self, tmp_path: Path) -> None:
        base = tmp_path / ".env"
        base.write_text("DATABASE_URL=from_base\nDEBUG=true\n")
        profile_file = tmp_path / ".env.production"
        profile_file.write_text("DATABASE_URL=from_production\n")

        loader = Loader.with_default_sources(profile="production", base_path=base, environ={})

        assert loader.load() == {"DATABASE_URL": "from_production", "DEBUG": "true"}

    def test_real_env_var_overrides_everything(self, tmp_path: Path) -> None:
        base = tmp_path / ".env"
        base.write_text("DATABASE_URL=from_base\n")
        profile_file = tmp_path / ".env.production"
        profile_file.write_text("DATABASE_URL=from_production\n")

        loader = Loader.with_default_sources(
            profile="production",
            base_path=base,
            environ={"DATABASE_URL": "from_real_env"},
        )

        assert loader.load() == {"DATABASE_URL": "from_real_env"}

    def test_without_profile_only_base_and_env_used(self, tmp_path: Path) -> None:
        base = tmp_path / ".env"
        base.write_text("DATABASE_URL=from_base\n")

        loader = Loader.with_default_sources(base_path=base, environ={"EXTRA": "from_env"})

        assert loader.load() == {"DATABASE_URL": "from_base", "EXTRA": "from_env"}

    def test_missing_profile_file_is_silently_ignored(self, tmp_path: Path) -> None:
        base = tmp_path / ".env"
        base.write_text("DATABASE_URL=from_base\n")

        # Perfil "staging" não tem arquivo .env.staging criado — não deve
        # quebrar, só não contribui com nenhum valor extra.
        loader = Loader.with_default_sources(profile="staging", base_path=base, environ={})

        assert loader.load() == {"DATABASE_URL": "from_base"}

    def test_missing_base_file_and_present_profile_file(self, tmp_path: Path) -> None:
        # Caso incomum mas válido: sem .env base, só .env.production.
        profile_file = tmp_path / ".env.production"
        profile_file.write_text("DATABASE_URL=from_production\n")
        base = tmp_path / ".env"  # não criado

        loader = Loader.with_default_sources(profile="production", base_path=base, environ={})

        assert loader.load() == {"DATABASE_URL": "from_production"}
