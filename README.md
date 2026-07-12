# config-validator

![CI](https://github.com/tensairod/config-validator/actions/workflows/ci.yml/badge.svg)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-blue)

> Type-safe configuration loading and validation that fails fast, clear,
> and at boot time — never in production, at 3am, because an env var
> was missing.

## O problema

Todo sistema em produção precisa de configuração: URLs de banco, chaves
de API, timeouts, feature flags. O problema recorrente:

- Configuração errada só é descoberta em runtime — às vezes em produção.
- `os.environ.get()` espalhado pelo código, sem validação central, sem
  tipo, sem default documentado.
- Bibliotecas de configuração comuns cobrem o básico (ler uma env var,
  converter um tipo), mas não expressam **regras de negócio compostas**
  (ex: "se `ENV=production`, `DEBUG` deve ser `false`").

`config-validator` resolve isso com um schema declarativo, validação
agregada (todos os erros de uma vez, não um por um) e uma CLI para
checar a configuração *antes* do deploy, não depois.

## Instalação

```bash
pip install config-validator
```

## Uso — biblioteca

```python
from enum import Enum

from config_validator.application.config_builder import ConfigBuilder
from config_validator.application.loader import Loader
from config_validator.application.validator import Validator
from config_validator.domain.cross_validator import cross_validator
from config_validator.domain.field import Field, FieldKind
from config_validator.domain.schema import Schema


class Environment(Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"


@cross_validator(name="debug_disabled_in_production")
def check_debug(values):
    if values.get("env") == Environment.PRODUCTION and values.get("debug") is True:
        return "DEBUG deve ser false quando ENV=production."
    return None


schema = Schema.of(
    Field(name="database_url", kind=FieldKind.STR, description="URL do PostgreSQL."),
    Field(name="port", kind=FieldKind.INT, required=False, default=8080),
    Field(name="debug", kind=FieldKind.BOOL, required=False, default=False),
    Field(name="env", kind=FieldKind.ENUM, enum_class=Environment),
    Field(name="api_key", kind=FieldKind.STR, secret=True),
    Field(name="db__host", kind=FieldKind.STR, required=False, default="localhost"),
    Field(name="db__port", kind=FieldKind.INT, required=False, default=5432),
    cross_validators=(check_debug,),
)

# 1. Carrega valores brutos de .env + variáveis de ambiente reais,
#    com precedência: env var real > .env.{profile} > .env base.
loader = Loader.with_default_sources(profile="production")
raw_values = loader.load()

# 2. Valida e coerciona os tipos. Levanta ConfigValidationError com
#    TODOS os erros agregados de uma vez, se algo estiver errado.
resolved = Validator().validate(schema, raw_values)

# 3. Monta o objeto de configuração final, navegável por atributo.
config = ConfigBuilder().build(schema, resolved)

print(config.database_url)
print(config.db.host)       # namespace resolvido a partir de "db__host"
print(config.api_key)       # SecretValue — nunca aparece em repr()/logs
print(config.api_key.reveal())  # único jeito de acessar o valor real
```

## Uso — CLI

Pensada para rodar em CI/CD antes do deploy, ou localmente durante o
desenvolvimento.

```bash
# Valida a configuração sem subir a aplicação. Exit code 0 (válida) ou 1 (inválida).
config-validator check --schema myapp.config:schema --env-file .env --profile production

# Lista todos os campos esperados, em tabela legível.
config-validator docs --schema myapp.config:schema

# Mesma coisa, em JSON (útil para scripts/ferramentas externas).
config-validator docs --schema myapp.config:schema --format json

# Gera um .env.example pronto para uso.
config-validator docs --schema myapp.config:schema --format env > .env.example
```

O caminho `--schema` segue o padrão `modulo:atributo` — o mesmo usado por
`uvicorn app:app` ou `gunicorn` — já que um Schema é código Python real
(`Field`, `CrossValidator`), não algo serializável em YAML/TOML sem
perder expressividade.

## Features

- ✅ Carregamento de configuração de variáveis de ambiente + `.env`, com
  precedência clara (env var real > `.env.{profile}` > `.env` base).
- ✅ Validação de tipos: `str`, `int`, `bool`, `float`, `list`, `enum`,
  `URL`, `path` — com coerção via Pydantic v2.
- ✅ Validações cruzadas entre campos (`@cross_validator`).
- ✅ Segredos (`secret=True`) nunca aparecem em `repr()`/`str()`/logs —
  em nenhum ponto do pipeline, do `Field` ao objeto de configuração final.
- ✅ Namespaces via `__` no nome do campo (`db__host` → `config.db.host`).
- ✅ Erros de validação **agregados** — todos de uma vez, com mensagens
  acionáveis, não um por vez.
- ✅ Múltiplos perfis de ambiente (`development`/`staging`/`production`,
  ou qualquer nome que fizer sentido para o seu projeto).
- ✅ CLI (`check`, `docs`) para uso em CI/CD e geração de documentação.
- ✅ 100% type-hinted, `mypy --strict` limpo, 100% de cobertura de testes.

## Arquitetura

O projeto segue uma arquitetura em camadas (Domain → Application →
Infrastructure → Interface), com as dependências sempre apontando para
dentro. Detalhes completos, diagramas e ADRs em
[`docs/architecture.md`](docs/architecture.md).

## Desenvolvimento

```bash
git clone https://github.com/SEU_USUARIO/config-validator.git
cd config-validator
pip install -e ".[dev]"

# Roda lint + type-check + testes, igual ao CI:
docker-compose run all

# Ou individualmente:
ruff check .
mypy src
pytest
```

## Roadmap

- [ ] `--format markdown` para o comando `docs` (colar direto num README).
- [ ] Integração com secrets managers (Vault, AWS Secrets Manager) como
  uma nova `ConfigSource`.
- [ ] Suporte a YAML como fonte adicional (avaliado e cortado da v1 para
  manter o escopo enxuto — ver requisitos do projeto).

## Contribuindo

Veja [`CONTRIBUTING.md`](CONTRIBUTING.md) *(ainda não criado — planejado
para antes da release pública)*.

## Licença

MIT — veja [`LICENSE`](LICENSE).
