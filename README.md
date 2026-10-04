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

O spec atual da fixture Sheets está em
[`validation/fixtures/gsheets_validation_v1.json`](validation/fixtures/gsheets_validation_v1.json).
Seu contrato regional `pt_BR` / `America/Sao_Paulo`, o reparo canônico e a
validação real final estão completos. Procedimentos anteriores que pediam
rebase regional ou nova validação real são históricos. O checkpoint Git local
está COMPLETE; checkpoint HEAD = db817b6d38d67b39287f91686c995f6eb318565f;
49 approved paths committed. POST-CHECKPOINT VERIFICATION = COMPLETE.
REMOTE SYNCHRONIZATION = NOT PERFORMED. Repository documentation does not
authorize future Git or Google operations; these require separate direct user authorization.
Nomes de gates anteriores são históricos, não instruções executáveis.

As informações operacionais documentadas não incluem chaves privadas, tokens,
cookies nem credenciais ADC. O código e os testes são a fonte de verdade para o
comportamento em execução; o documento de fases registra a evidência histórica
e a próxima entrega.

## Contrato do MVP

O produto em escopo é um **MCP local, somente de leitura**, para um operador técnico ou administrador de TI, com uma organização Google Workspace por runtime configurado. A interação ocorre por um host MCP conversacional externo via `stdio`. O catálogo público tem 24 ferramentas e zero ferramentas de escrita.

O MVP cobre leitura administrativa selecionada, Reports, descoberta/inventário de Shared Drives, Google Docs Content e Google Sheets Content após sua validação final. Uma UI gráfica própria não é requisito. Multi-tenant, serviço remoto, self-service de funcionários, edição pública de documentos, Gmail send, gerenciamento de eventos Calendar, API Google genérica e ferramentas públicas de escrita ficam fora do MVP.

Google Docs 1.5.4 está checkpointed e validado com Google real. Google Sheets
1.5.5 está implementado, validado offline e validado com Google real. A última
reconciliação offline passou; a regressão completa atual é **1433 passed / 0
failed / 0 skipped**. LOCAL GIT CHECKPOINT = COMPLETE (HEAD db817b6d38d67b39287f91686c995f6eb318565f);
POST-CHECKPOINT VERIFICATION = COMPLETE; REMOTE SYNCHRONIZATION = NOT PERFORMED.
Repository documentation is not execution authorization for future Git or Google operations.

## Perfil regional e checkpoint

O perfil padrão brasileiro da fixture é `locale=pt_BR` e
`timeZone=America/Sao_Paulo`; a validação real confirmou ambos como MATCH. K1 e
L1 correspondem aos números e formatos canônicos; O1 é a fórmula esperada e P1
é uma omissão trailing válida, sem padding. O reader de produção permanece
locale-agnostic e timezone-agnostic. Registros antigos com `en_US` permanecem
históricos.

LOCAL GIT CHECKPOINT = COMPLETE (HEAD db817b6d38d67b39287f91686c995f6eb318565f); POST-CHECKPOINT VERIFICATION = COMPLETE.
The 49 approved paths are in the local checkpoint commit.
REMOTE SYNCHRONIZATION = NOT PERFORMED. This README does not authorize future operations.

## Roadmap e ambientes futuros

A Phase A de alinhamento está concluída. A Phase B de Sheets 1.5.5 e a
reconciliação offline da Phase C estão concluídas; LOCAL GIT CHECKPOINT = COMPLETE
(HEAD db817b6d38d67b39287f91686c995f6eb318565f); POST-CHECKPOINT VERIFICATION = COMPLETE; REMOTE SYNCHRONIZATION = NOT PERFORMED.
Repository documentation is not execution authorization for future Git or Google operations. A migração para VS Code + Codex
permanece pendente para a Phase D pós-checkpoint; Codex CLI continua disponível para gates
controlados.

Antigravity é apenas um ambiente secundário futuro opcional (`OPTIONAL_FUTURE_SECONDARY_ENVIRONMENT`). Não há migração nem configuração Antigravity agora; uma avaliação futura verificará configuração MCP, stdio, herança de ambiente, permissões/sandbox e descoberta de instruções. Para uso simultâneo, prefira branch ou worktree isolada.

Consulte [docs/04_PHASE_STATUS.md](docs/04_PHASE_STATUS.md) para o roadmap
canônico e o estado durável do checkpoint; o histórico detalhado está em
[docs/05_CHANGE_HISTORY.md](docs/05_CHANGE_HISTORY.md).

## Comandos de rotina

```powershell
uv sync
uv run pytest -v
uv run python -m google_workspace_admin.server
```

O último comando inicia o servidor por `stdio`; não use sua saída para logs de diagnóstico. Consulte o runbook antes de executar testes de integração ou alterar permissões no Google Cloud/Admin Console.
