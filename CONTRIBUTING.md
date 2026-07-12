# Contribuindo com config-validator

## Ambiente de desenvolvimento

```bash
git clone https://github.com/SEU_USUARIO/config-validator.git
cd config-validator
pip install -e ".[dev]"
```

Ou, para reproduzir exatamente o ambiente do CI, via Docker:

```bash
docker-compose run all   # lint + type-check + testes
```

## Antes de abrir um PR

Rode localmente e confirme que tudo passa:

```bash
ruff check .
mypy src
pytest --cov-report=term-missing
```

Cobertura mínima exigida: 90% (o CI falha automaticamente abaixo disso).
Este projeto mantém 100% como padrão de fato — se sua mudança reduzir a
cobertura, adicione os testes que faltam antes de abrir o PR.

## Convenções de Git

- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`, `style:`).
- **Branches:** `feature/{número-da-issue}-{descrição-curta}`.
- **PRs:** sempre atrelados a uma issue existente. Descreva o quê e,
  principalmente, o *porquê* da mudança — decisões de design não óbvias
  merecem uma frase de justificativa no corpo do commit ou do PR.
- **Squash merge** para manter o histórico de `main` limpo.

## Estrutura do projeto

O projeto segue uma arquitetura em camadas (Domain → Application →
Infrastructure → Interface/CLI). Antes de adicionar código novo, veja
[`docs/architecture.md`](docs/architecture.md) para entender onde cada
tipo de responsabilidade deve morar — e os ADRs que já justificam várias
decisões estruturais do projeto.

## Reportando bugs / sugerindo features

Abra uma issue descrevendo o comportamento esperado vs. o observado (para
bugs) ou o problema real que a feature resolveria (para sugestões).
