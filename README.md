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

## Estado atual

A Fase 1.5.1 — Shared Drive Discovery está implementada e validada com
`workspace_drives_list` e `workspace_drive_get`. A Fase 1.5.2 — Drive File
Inventory está implementada localmente e validada em RV2 pelo MCP hospedado,
com
`workspace_drive_files_list`. A Fase 1.5.4 adiciona o primeiro reader concreto,
`workspace_file_content_read`, exclusivamente para Google Docs estruturados.
O catálogo possui 24 tools read-only: 20 Read, 4 Content e 0 Write. O
binding operacional Content usa as cinco variáveis process-only configuradas
na tabela MCP e o bootstrap é lazy/fail-closed. A REAL VALIDATION RV2 foi
executada uma única vez pelo MCP hospedado: a cadeia keyless alcançou a Drive
API, retornou uma página limitada e não expôs valores sensíveis. O FINAL REVIEW
V1 de 1.5.1 passou e o CHECKPOINT V1 está preservado. Para 1.5.2, PLAN V1,
IMPLEMENT V1, REAL VALIDATION RV2, FINAL REVIEW V1 e CHECKPOINT V1 estão
completos; a etapa 1.5.2 está encerrada e o próximo gate exige autorização
explícita para o próximo estágio de Content.

## Comandos de rotina

```powershell
uv sync
uv run pytest -v
uv run python -m google_workspace_admin.server
```

O último comando inicia o servidor por `stdio`; não use sua saída para logs de
diagnóstico. Consulte o runbook antes de executar testes de integração ou
alterar permissões no Google Cloud/Admin Console.

A etapa 1.5.3 — Content Reading Architecture & Safety implementa o
substrate interno comum: routing MIME fechado, budgets finitos, snapshots de
inventário, chunks normalizados, provenance, outcomes explícitos, preflight e
políticas contra conteúdo ativo. Todo arquivo inventariado deverá futuramente
resultar em conteúdo processado ou em estado terminal explícito.
PLAN V1 e IMPLEMENT V1 estão completos. Como 1.5.3 não adiciona operação
Google nem tool Content executável, FINAL REVIEW V1 = COMPLETE; REAL GOOGLE
VALIDATION = NOT APPLICABLE / NOT EXECUTED; CHECKPOINT V1 = COMPLETE. A
etapa 1.5.4 — Google Docs Content reutiliza esse substrate com Docs API
estruturada, tabs recursivas, body/tabelas/headers/footers/footnotes, chunking
local e continuation opaca. O fluxo faz Drive metadata preflight e postflight
antes de liberar chunks; imagens, drawings, charts e equations não lidos
produzem `PARTIALLY_PROCESSED`, nunca sucesso silencioso. Comentários e comment
threads Developer Preview estão explicitamente fora da V1. A recepção usa o
stream codificado do HTTPX, limita separadamente bytes raw/wire e bytes
decodificados a 32 MiB e só então materializa o JSON; `Content-Length` é apenas
uma otimização de rejeição antecipada. `identity`, `gzip` e `deflate` possuem
decodificação incremental limitada; outros encodings falham fechados.

PLAN V1 e IMPLEMENT V1 estão completos somente localmente. PRE-RV REVIEW V1 =
BLOCKED registrou seis findings e PRE-RV REMEDIATION V1/V2 = COMPLETE corrigiu
e reconfirmou os seis. O PRE-RV RE-REVIEW V1 permaneceu BLOCKED exclusivamente
pelo finding de cobertura RR-P2-01; RR-P2-01 REMEDIATION V1 = COMPLETE adicionou
12 testes adversariais permanentes, elevando Google Docs a 59 casos e a regressão
local a 897 casos aprovados, sem mudança em source. PRE-RV FINAL RE-REVIEW V1 =
PASS. Real auth, discovery e target resolution = PASS. REAL CONTENT VALIDATION
V2 = BLOCKED com `EXTRACTION_FAILED`; FAILURE OBSERVABILITY IMPLEMENT V1 e
REMEDIATION V2 = COMPLETE / LOCAL VALIDATION. A validação real de conteúdo
pós-remediação permanece PENDING; 1.5.4 ainda NÃO está completa e não há
checkpoint desta etapa. A Docs API (`docs.googleapis.com`) foi habilitada para
a validação manual, sem alterar o escopo read-only.
