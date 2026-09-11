# Google Workspace Admin MCP

Servidor MCP local para inventário administrativo do Google Workspace. A camada
atual é exclusivamente de leitura e usa autenticação sem chave privada:

`ADC -> IAM Credentials signJwt -> Domain-Wide Delegation -> OAuth 2.0 -> Admin SDK`

## Documentação operacional

Leia nesta ordem antes de alterar ou operar o projeto:

1. [Guia para agentes](docs/00_AGENT_GUIDE.md)
2. [Arquitetura e configuração Google](docs/01_GOOGLE_CONFIGURATION.md)
3. [Catálogo MCP](docs/02_MCP_CATALOG.md)
4. [Runbook de operação e desenvolvimento](docs/03_OPERATING_RUNBOOK.md)
5. [Andamento das fases](docs/04_PHASE_STATUS.md)
6. [Histórico de marcos](docs/05_CHANGE_HISTORY.md)

As informações operacionais documentadas não incluem chaves privadas, tokens,
cookies nem credenciais ADC. O código e os testes são a fonte de verdade para o
comportamento em execução; o documento de fases registra a evidência histórica
e a próxima entrega.

## Comandos de rotina

```powershell
uv sync
uv run pytest -v
uv run python -m google_workspace_admin.server
```

O último comando inicia o servidor por `stdio`; não use sua saída para logs de
diagnóstico. Consulte o runbook antes de executar testes de integração ou
alterar permissões no Google Cloud/Admin Console.
