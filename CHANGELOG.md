# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto segue [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [1.0.0] - Unreleased

### Adicionado

**Domain Core**
- `Field`: representa um campo de configuração individual (nome, tipo,
  obrigatoriedade, default, descrição, flag de segredo). Suporta os tipos
  `str`, `int`, `bool`, `float`, `list`, `enum`, `url` e `path`.
- `Schema`: agrupa múltiplos `Field`s, resolve namespaces via prefixo
  duplo underscore (`db__host` → `config.db.host`) e detecta colisões de
  namespace na criação.
- `CrossValidator` / `@cross_validator`: validações que dependem de mais
  de um campo simultaneamente (ex: "`DEBUG` deve ser `false` quando
  `ENV=production`").
- `SecretValue`: envelope opaco para valores sensíveis, nunca revelados
  via `repr()`/`str()`/f-strings — o valor real só é acessível via
  `.reveal()`.

**Sources & Loader**
- `ConfigSource` (protocolo), `EnvVarSource` e `DotEnvSource`: leitura de
  variáveis de ambiente reais e de arquivos `.env`.
- `Loader`: compõe múltiplas `ConfigSource` e resolve precedência
  (variável de ambiente real > `.env.{profile}` > `.env` base).

**Validation & Errors**
- `Validator`: valida e coerciona os valores brutos contra um `Schema`,
  usando Pydantic v2 como motor de tipos.
- Erros de validação são **agregados** — todas as violações de uma vez,
  nunca fail-fast na primeira. Mensagens de erro são acionáveis (dizem o
  que fazer, não só o que está errado).
- Valores de campos marcados como `secret=True` são automaticamente
  envolvidos em `SecretValue`, tanto vindos de `default` quanto de fontes
  reais (env var/`.env`).
- `ConfigBuilder` / `ConfigNamespace`: monta o objeto de configuração
  final, imutável e navegável por atributo, resolvendo namespaces.

**CLI**
- `config-validator check --schema modulo:atributo [--env-file] [--profile]`:
  valida a configuração sem subir a aplicação. Exit code 0 (válida) ou 1
  (inválida) — pensado para uso em pipelines de CI/CD.
- `config-validator docs --schema modulo:atributo [--format table|json|env]`:
  lista todos os campos esperados. O formato `env` gera um
  `.env.example` pronto para uso.

**Infraestrutura do projeto**
- Suíte de testes com 100% de cobertura (branch incluído), `ruff` e
  `mypy --strict` limpos.
- CI (GitHub Actions): lint, type-check, testes em matriz Python
  3.10/3.11/3.12, scan de segurança de dependências (`pip-audit`) e build
  do pacote.
- Ambiente de desenvolvimento reprodutível via Docker/docker-compose.

### Notas de arquitetura

Ver [`docs/architecture.md`](docs/architecture.md) para o detalhamento
completo de decisões arquiteturais (ADRs), diagramas e débitos técnicos
conscientemente adiados.
