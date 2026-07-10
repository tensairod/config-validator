# Dockerfile de desenvolvimento/CI para config-validator.
#
# Decisão arquitetural: como este projeto é uma BIBLIOTECA (não um serviço),
# o Docker aqui não serve para "rodar a aplicação" — serve para garantir um
# ambiente reprodutível de lint/testes/type-check, idêntico ao que roda no CI.
# Isso elimina o clássico "na minha máquina funciona" também para bibliotecas.

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Copia apenas os arquivos de definição de dependências primeiro,
# para aproveitar cache de camadas do Docker em rebuilds.
COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --upgrade pip && \
    pip install -e ".[dev]"

COPY tests/ ./tests/
COPY docs/ ./docs/

# Comando padrão: roda a suíte completa de qualidade (lint + type-check + testes).
# Cada etapa pode ser rodada isoladamente via docker-compose (ver docker-compose.yml).
CMD ["sh", "-c", "ruff check . && mypy . && pytest"]
