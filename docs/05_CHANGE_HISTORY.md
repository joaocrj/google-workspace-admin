# Histórico de marcos

| Data | Commit | Marco |
| --- | --- | --- |
| 03/09/2026 | `f0843f0` | Autenticação keyless ADC → IAM `signJwt` → DWD → OAuth e consulta Directory inicial |
| 03/09/2026 | `4d9121f` | Servidor MCP e ferramentas de usuários |
| 07/09/2026 | `aae5f18` | Cache de tokens em memória, serialização e testes MCP de usuários |
| 07/09/2026 | `ee92e06` | Diretrizes de manutenção do Google Workspace Admin MCP |
| 07/09/2026 | `0870c2a` | Listagem de grupos |
| 08/09/2026 | `c9f5fc7` | Listagem de membros de grupos |
| 08/09/2026 | `8ab05e7` | Listagem de unidades organizacionais |
| 10/09/2026 | `6c3cc87` | Listagem de dispositivos móveis |
| 10/09/2026 | `0610ebd` | Listagem de dispositivos ChromeOS |
| 10/09/2026 | `b589a91` | Funções administrativas e atribuições |
| 10/09/2026 | `581b7d9` | Listagem de domínios |
| 10/09/2026 | `c01fd11` | Listagem de aliases de domínio e correções de regressão/serialização |
| 11/09/2026 | `9ce707f` | Implementação local de Buildings: Directory API, serialização, paginação por token e 76/76 testes; após reautenticação manual da ADC pelo usuário, DWD/privilégio delegado confirmados e validação MCP real concluída com 0 Buildings e sem próxima página; checkpoint desta entrega |
| 11/09/2026 | `16565d6` | Resources / Salas: implementação local de `resources.calendars`, serialização limitada, paginação por token, ordenação/filtro e 14ª tool MCP; 100/100 testes locais e validação MCP real da cadeia keyless concluídos com 0 recursos e sem página seguinte; checkpoint registrado nesta entrega |
| 11/09/2026 | checkpoint desta entrega | Features: PLAN, implementação local de `resources.features`, serialização limitada a `feature_name`, paginação por token e 15ª tool MCP; 121/121 testes locais e validação MCP real da cadeia keyless concluídos com 0 Features e sem página seguinte; checkpoint encerra Features e Calendar — recursos corporativos |
| 11/09/2026 | checkpoint concluído | Admin Audit: PLAN, implementação local de `reports.activities.list` com `applicationName=admin`, launcher MCP Python da `.venv`, 16ª tool MCP e 155/155 testes locais; REAL VALIDATION MCP executada uma única vez com sucesso, 1 Activity e próxima página presente; DWD `admin.reports.audit.readonly` e sujeito Superadministrador confirmados manualmente; nenhum conteúdo de auditoria registrado |
| 11/09/2026 | histórico — superado pelo checkpoint seguinte | Login Audit: PLAN e implementação local de `activities.list` com `applicationName=login`, serializer conservador, 17ª tool MCP e **191/191 testes locais aprovados**; REAL VALIDATION e checkpoint Git pendentes naquele momento; nenhuma chamada Google ou alteração administrativa realizada |
| 11/09/2026 | checkpoint desta entrega | Login Audit: redescoberta pós-restart pelo host, uma única chamada MCP com `max_results=1`, sucesso, 1 Activity e próxima página presente; **191/191 testes locais aprovados** e `git diff --check` aprovado; nenhum conteúdo de Activity, PII, credencial ou token registrado; checkpoint concluído |
| 11/09/2026 | implementação pendente de checkpoint | Drive Audit: PLAN e IMPLEMENT concluídos com módulo independente `reports/drive_audit.py`, serializer allowlist específico, 18ª tool MCP e **230/230 testes locais aprovados** pelo Python direto da `.venv`; REAL VALIDATION concluída exclusivamente pelo MCP original com exatamente uma chamada `max_results=1`, sucesso, 1 Activity e próxima página presente; nenhum conteúdo real de Activity persistido |
| 12/09/2026 | histórico — superado pela validação V9 | User Usage: IMPLEMENT local de `reports/user_usage.py` com `userUsageReport.get`, 19ª tool MCP, scope `admin.reports.usage.readonly`, validação estrita de data, uma página por chamada, timeout de 30 segundos e nenhum retry; serializer allowlistado com `profile_id`, `timestamp_last_login` como nome atual, timestamps condicionais e warnings sanitizados; REAL VALIDATION não executada naquele checkpoint |
| 12/09/2026 | documentação pós-REAL VALIDATION; checkpoint pendente | User Usage: validação final de `UserUsageReport.get` executada com sucesso em `2026-09-12` com a tool `workspace_user_usage_get`; catálogo 18 → 19; serializer e allowlists confirmados; warnings sanitizados; uma página por chamada e sem retry; **264 testes finais aprovados**; data do relatório solicitado: `date=2026-09-10`, `max_results=1`, `parameters=accounts:used_quota_in_percentage`, `user_key=all`, `usageReports=1`, próxima página presente e warnings presentes (1) |
| 12/09/2026 | histórico — superado pela consolidação Read | Customer Usage: `CustomerUsageReports.get` no módulo `reports/customer_usage.py`, tool `workspace_customer_usage_get`, catálogo 19 → 20, `parameters` obrigatório, allowlist inicial de dez métricas integer de Accounts, serializer allowlist-first, warnings sanitizados, `pageToken`/`nextPageToken` normalizados, uma página por chamada, sem retry e timeout de 30 segundos; **307 testes locais aprovados**; nenhuma chamada Google realizada naquele checkpoint |
| 12/09/2026 | checkpoint / commit concluído | Customer Usage: REAL VALIDATION V9 e FINAL REVIEW concluídas com sucesso; uma chamada real, sem retry ou paginação, `usageReports=1`, `next_page_token` ausente e warnings presentes (1); **307 testes aprovados**; commit `6624305e8a60de09efda5b6626b317755c07536c` com a mensagem `feat: add workspace customer usage reports` |
| 12/09/2026 | PLAN V1 concluído | Consolidação da camada Read: auditoria transversal identificou 3 P1, 7 P2, 3 P3 e 1 P4; sem P0; escopo fechado para paginação explícita, scopes readonly, erros seguros, serializers, validação, testes e documentação |
| 12/09/2026 | IMPLEMENT V1 concluído — sem commit | Consolidação da camada Read: sete Directory tools com `page_token` explícito e `next_page_token`, targets de scope readonly no código, helper HTTP seguro, DWD sem raw body, aliases aninhados allowlistados, validação de shapes/inputs, catálogo local com 20 tools e **398 testes locais aprovados**; DWD manual pendente; nenhuma chamada Google, Workspace ou MCP funcional |
| 13/09/2026 | REMEDIATION IMPLEMENT V1 concluído — sem commit | DWD Users: observabilidade de erros estruturada e segura com `code`, `layer`, `operation` e `http_status`; categorias ADC, IAM `signJwt`, DWD OAuth, Workspace HTTP, validação de resposta, validação local e fallback inesperado; testes de redaction e protocolo preservados; nenhuma chamada Google, Workspace ou MCP funcional |
| 13/09/2026 | REAL VALIDATION V3 bloqueada — sem commit | DWD Users: uma única chamada limitada foi executada após a remediação; o executor não disponibilizou `code`, `layer`, `operation` ou `http_status`, portanto a classificação permanece D9. Sem retry, paginação, dados de usuário, alteração DWD/ADC ou validação de Groups; possível host stale permanece não confirmado |
| 13/09/2026 | POST-RESTART HOST VALIDATION V1 concluída — sem commit | Após restart completo manual do Codex e reautenticação ADC manual pelo usuário, o host expôs 20 tools e `workspace_users_list` com `max_results`/`page_token`; source/host em MATCH. A remediação interna é inferida do host novo; Users continua aguardando real validation V4; nenhuma chamada Google ou alteração de configuração foi feita |
| 13/09/2026 | REAL VALIDATION V4 concluída — sem commit | DWD Users: uma única chamada real limitada a `max_results=1` foi concluída com sucesso; `users_count=1`, `next_page_token` presente e não utilizado; scope `admin.directory.user.readonly`; nenhum registro de usuário foi reportado; sem retry, paginação adicional ou validação de Groups |
| 13/09/2026 | GROUP READONLY REAL VALIDATION V1 concluída — sem commit | DWD Groups: uma única chamada real limitada a `max_results=1` foi concluída com sucesso; `groups_count=1`, `next_page_token` ausente; scope `admin.directory.group.readonly`; nenhum registro de grupo foi reportado; sem retry, paginação adicional ou validação de Group Members |
| 13/09/2026 | GROUP MEMBER READONLY REAL VALIDATION V1 bloqueada — sem commit | Não havia `group_key` real disponível em contexto local permitido; valores de teste não foram usados e nenhuma chamada Groups ou Group Members foi executada. Próximo ponteiro: MANUAL GROUP KEY INPUT |
| 13/09/2026 | GROUP MEMBER READONLY REAL VALIDATION V1 concluída — sem commit | DWD Group Members: uma única chamada real limitada a `max_results=1` foi concluída com sucesso; `members_count=0`, `next_page_token` ausente; scope `admin.directory.group.member.readonly`; nenhum dado de membro ou identificador foi reportado; sem retry, paginação adicional ou validação de OrgUnits |
| 13/09/2026 | GROUP MEMBER READONLY REAL VALIDATION V2 concluída — sem commit | DWD Group Members: após entrada manual transitória do identificador, uma única chamada real limitada a `max_results=1` foi concluída com sucesso; `members_count=0`, `next_page_token` ausente; scope `admin.directory.group.member.readonly`; nenhum identificador ou dado de membro foi reportado; sem retry, paginação adicional ou validação de OrgUnits |
| 13/09/2026 | ORGUNIT READONLY REAL VALIDATION V1 concluída — sem commit | DWD OrgUnits: uma única chamada real mínima com consulta de filhos na raiz foi concluída com sucesso; `orgunits_count=2`; paginação não suportada pela tool; scope `admin.directory.orgunit.readonly`; nenhum dado de OU foi reportado; sem retry ou chamadas adicionais |
| 13/09/2026 | REMEDIATION PLAN V1 concluído — sem commit | Plano mínimo para FR-01 a FR-04: validação inteira estrita na fronteira MCP, normalização de operações, remoção de identificador real das fixtures e sincronização documental; nenhuma chamada Google ou alteração de configuração |
| 13/09/2026 | REMEDIATION IMPLEMENT V1 concluído — sem commit | FR-01 corrigido com `StrictInt` nos 14 `max_results` públicos e rejeição antes da execução; FR-02 corrigido com quatro operações canônicas; FR-03 substituído por fixture reservada; FR-04 sincronizado em docs/01–05; **459 testes locais aprovados**, incluindo 48 casos novos de fronteira/operação; catálogo com 20 tools; nenhuma chamada Google, DWD/IAM ou alteração administrativa |

## READ CONSOLIDATION FINAL REVIEW V1 — 13/09/2026

**BLOCKED**, apesar de `uv run pytest -q` confirmar **411 passed**. Baseline
`master` / `6624305e8a60de09efda5b6626b317755c07536c`, 25 caminhos autorizados,
nenhum inesperado, staging vazio e catálogo com 20 tools preservados.

Achados registrados em docs/04: **FR-01** (P1), coerção de bool/float/string
numérica antes da validação inteira nas sete tools Directory; **FR-02** (P2),
quatro operações degradadas para `unknown` no helper seguro; **FR-03** (P2),
identificador real em quatro literais de fixtures já existentes no HEAD,
sem reproduzir seu valor; **FR-04** (P2), documentação de migração, cobertura
de erros e árvore de validação divergente do estado final.

As quatro validações readonly continuam PASSED e todo o histórico anterior
foi preservado. Source, testes e configuração não foram alterados nesta
revisão. Nenhuma chamada Google/Workspace/MCP funcional/DWD/IAM foi realizada;
nenhum staging, commit ou push. Próximo ponteiro:
**READ CONSOLIDATION REMEDIATION**. CHECKPOINT / COMMIT permanece pendente.

## READ CONSOLIDATION FINAL REVIEW V2 — 13/09/2026

**PASSED**, sem commit. A revisão integral confirmou FR-01, FR-02, FR-03 e
FR-04 como **FIXED / VERIFIED**: os 14 `max_results` públicos usam validação
estrita na fronteira MCP; as quatro operações conhecidas preservam contexto
canônico; as fixtures usam identificadores reservados; e docs/01–05 estão
sincronizados. Targeted tests passaram em **272** casos e a suíte completa em
**459** casos. O catálogo permaneceu com 20 tools, `mcp.run()` permaneceu a
operação final, não houve alteração de semântica Google, chamadas externas ou
exposição sensível. FINAL REVIEW V1 = BLOCKED e todos os seus achados/histórico
foram preservados. Próximo ponteiro: **READ CONSOLIDATION CHECKPOINT / COMMIT**.

## READ LAYER CONSOLIDATION CHECKPOINT / COMMIT V1 — 13/09/2026

**COMPLETE**, registrado neste commit, sem push. O checkpoint consolida o
FINAL REVIEW V2 = PASSED, FR-01 a FR-04 = FIXED / VERIFIED, catálogo com 20
tools e suíte local com 459 testes aprovados. O working tree e o staging devem
permanecer limpos após a criação deste único commit. Nenhuma chamada Google,
Workspace ou MCP funcional foi realizada e nenhuma próxima fase foi iniciada.

## Lições registradas

- O scope ChromeOS não estava autorizado inicialmente; foi incluído antes do
  teste direto e a API retornou HTTP 200 sem dispositivos.
- Para roles, a API retornou 15 funções e 3 atribuições; uma contagem textual
  posterior incorreta não representou falha da integração.
- A primeira redescoberta do catálogo após aliases mostrou um catálogo antigo.
  O encerramento do processo anterior e a reinicialização permitiram ao Codex
  descobrir a ferramenta nova.
- Serializadores auxiliares não devem receber `@mcp.tool()`. A regressão em
  `workspace_users_list` foi corrigida ao restaurar o decorador da ferramenta.
- O checkpoint `c01fd11` também normalizou `test_mcp_protocol.py` para UTF-8
  sem BOM, LF e exatamente uma quebra de linha no EOF.
- Buildings usa `resources.buildings` da Admin SDK Directory API, não a Google
  Calendar API. O scope readonly de recursos de Calendar foi confirmado na DWD
  por um Superadministrador. Depois de o usuário reautenticar manualmente a
  ADC, o processo MCP novo reconheceu a 13ª tool e a única chamada real
  autorizada retornou 0 Buildings, sem próxima página e sem retry.
- Resources / Salas usa a coleção irmã `resources.calendars` e o mesmo scope
  readonly de recursos de Calendar. O módulo encaminha `orderBy` e `query`
  apenas depois de rejeitar valores vazios, preserva o token de página e não
  expõe `kind`, `etags` ou `featureInstances`. Um processo MCP `stdio` novo
  redescobriu a 14ª tool e a única chamada real limitada retornou zero recursos,
  sem página seguinte; nenhum dado administrativo ou material de autenticação
  foi registrado.

- Admin Audit usa a Reports API, não a Directory API: o endpoint fixa
  `applicationName=admin`, enquanto `user_key` filtra o ator e não controla a
  impersonação DWD. A implementação limita páginas a 100 registros, rejeita
  datas não RFC 3339 e omite estruturalmente `sensitiveParameters` e dados
  brutos. A DWD e o privilégio Superadministrador foram confirmados
  manualmente; a única chamada MCP real retornou 1 Activity e próxima página,
  sem registrar conteúdo de auditoria.
- As falhas anteriores ocorreram no ambiente `codexsandboxoffline`: acesso
  bloqueado ao OAuth, `UnsupportedOperation` no `fileno()` de um `stderr` não
  compatível e cache do `uv` sem permissão. O launcher foi remediado para o
  Python da `.venv`; o processo stdio novo inicializou com 16 tools. Nenhuma
  alteração administrativa foi feita.

- Login Audit foi implementado localmente como módulo independente da Reports
  API, com `applicationName=login` fixo, o mesmo scope readonly de auditoria,
  limite MCP de 1–100 por página, paginação explícita sem percurso automático,
  nenhuma nova tentativa e serializer específico com allowlist de valores de
  login. O catálogo passou a 17 tools e a suíte confirmou 191/191 testes
  locais; antes da tentativa 3, REAL VALIDATION e checkpoint Git permaneciam
  pendentes. Nenhum dado real de login, credencial, token, JWT ou alteração
  administrativa foi registrado nessa etapa.
- A linha do histórico operacional foi preservada: tentativa 1 com catálogo
  legado; rediscovery; tentativa 2 em `codexsandboxoffline` com `WinError 10013`;
  diagnóstico de contexto/rede; impossibilidade de restart do host dentro da
  sessão; restart manual do Codex; POST-RESTART CHECK; e tentativa 3 concluída
  pelo MCP do host com uma única chamada bem-sucedida. O resultado foi mantido
  sanitizado, sem Activity, PII ou material de autenticação.
- Drive Audit permanece separado de Drive Activity API v2 e usa somente
  `activities.list` com `applicationName=drive`. A implementação mantém o
  scope já utilizado por Admin Audit e Login Audit, uma página por chamada,
  `page_token` explícito e nenhum retry. O serializer é allowlistado para
  minimizar títulos, destinatários, queries, conteúdo e estruturas complexas,
  mantendo apenas os IDs opacos necessários à correlação administrativa. A
  documentação preserva a distinção entre janela de relatório de até 180 dias
  e retenção geral de seis meses; nenhuma regra artificial foi adicionada ao
  código. Em 11/09/2026, a REAL VALIDATION foi concluída exclusivamente pelo
  MCP original carregado pelo host com exatamente uma chamada
  `workspace_drive_audit_list(max_results=1)`: sucesso, 1 Activity e
  `next_page_token` presente. A cadeia keyless até a Reports API foi validada,
  sem retry ou paginação adicional e sem persistir conteúdo real de Activity,
  token, credencial ou payload. O CHECKPOINT foi concluído nesta entrega.
- User Usage usa a Reports API de User Usage, não `activities.list`, Drive
  Activity API ou `customerUsageReports`. A identidade devolvida é limitada a
  `entity.profileId` como `profile_id`; `userEmail` e `entityId` são omitidos.
  A allowlist aceita somente métricas numéricas, contagens, quotas e booleans
  administrativas das referências de Accounts, Docs, Gmail, Chat e Classroom;
  não há passthrough de `stringValue`, `msgValue`, estruturas desconhecidas ou
  parâmetros não allowlisted. `timestamp_last_login` substitui o nome antigo
  `last_login_time`, e os três timestamps de Accounts só são devolvidos quando
  explicitamente solicitados. A entrega local usa mocks; nenhuma chamada Google,
  alteração administrativa, staging, commit ou push foi feita.
- Na validação final de User Usage, falhas opacas iniciais ocorreram na camada
  de autenticação e o diagnóstico temporário identificou `RefreshError`. O
  usuário reautenticou manualmente a ADC; a validação seguinte obteve sucesso,
  sem alteração de código funcional, DWD, scopes ou Admin Console. Toda a
  instrumentação temporária foi removida antes do checkpoint, e campos
  diagnósticos temporários não fazem parte do contrato final.
- Customer Usage mantém contrato separado de User Usage: não expõe
  `maxResults`, `userKey`, `filters`, `orgUnitID` ou `customerId`; exige métricas
  explicitamente allowlisted, preserva paginação manual e não busca payload
  amplo por padrão. A primeira allowlist é deliberadamente limitada a dez
  métricas integer agregadas de Accounts; as demais aplicações ficam omitidas
  até uma revisão específica.

Este histórico resume fatos registrados no Git e no inventário do usuário; não
substitui o `git log`, os testes ou a validação de uma configuração atual do
Google Cloud/Admin Console.

## 14/09/2026 — WORKSPACE CONTENT FOUNDATION IMPLEMENT V1 — COMPLETE / SEM COMMIT

Implementada exclusivamente a fundação transversal local da Fase 1.5. Foram
adicionados profiles imutáveis de Content Research, `WorkspaceSubject`,
interface de resolução futura sem Directory lookup, registry fechado dos sete
profiles read-only oficialmente verificados, cache-key contratual separado por
profile/customer/Service Account/subject/scope profile, policy de domínio e
customer, guard positivo de operações, contratos bounded para Shared Drives,
`ContentReadTransport` mockável, retry opt-in para reads idempotentes, limites
de paginação/contexto, evidência determinística e audit events
pseudonimizados. O safe-error contract recebeu somente códigos justificados
pela Foundation.

Não foram criadas tools MCP Content: `workspace_drives_list`,
`workspace_drive_get` e `workspace_drive_files_list` continuam não
implementadas e não registradas. `server.py`, `config.py`, a autenticação Read
existente, DWD, ADC e o catálogo público com 20 tools permaneceram intactos.

Foram adicionados **28 testes** transversais; a regressão completa passou em
**487 testes** (**459 baseline + 28 Foundation**). Não houve chamada Google,
Drive, Gmail, Docs, Sheets, Slides, MCP funcional, DWD, IAM `signJwt` ou
geração de token. Não houve alteração de Service Account, scopes, APIs,
Admin Console, staging, commit ou push.

O estado canônico passou a ser: FASE 1.5 corrente, Architecture PLAN V1
complete, Official Google Verification V1 pass, Foundation Implement V1
complete; Write Layer PLAN preservado e implementação pausada. Shared Drive
RV1 e todas as validações reais de Content permanecem pendentes.

## 14/09/2026 — WORKSPACE CONTENT FOUNDATION REMEDIATION IMPLEMENT V1 — COMPLETE / SEM COMMIT

Remediados localmente FR-P0-01/02, FR-P1-01/02/03/04,
FR-P2-01/02/03/04 e FR-P3-01/02. A entrega adicionou `ContentAuthBroker`,
registry de profiles provisionados, filtros Drive estruturados, field masks
internas, caps explícitos de paginação, retry hard-capped, transport com
client de produção controlado e envelope JSON sem `httpx.Response` público.
Subjects passaram a ter validação por capability; `trashed=false` é invariável
no inventário; evidence IDs são gerados internamente; pseudônimos usam
HMAC-SHA256 com provider abstrato; `scope_summary` é fechado e estruturado.

Foram adicionados testes negativos para substituição de identidade/scopes,
bypass DWD, campos/q/lixeira, limites, redirects, JSON malformado, classes
sem retry, cancelamento, PII e HMAC. A execução direcionada passou em 59 testes
e a regressão completa passou em 518 testes, preservando os 487 testes
anteriores. O warning de cache pytest por permissão local permaneceu sem
impacto.

Não foram criadas tools Content ou Write; o catálogo público permanece com 20
tools e `mcp.run()` continua a operação final de `server.py`. Não houve
chamada Google/Drive/Gmail/Docs/Sheets/Slides/MCP funcional, token, DWD,
IAM `signJwt`, mudança de scopes, Service Account, Cloud, Admin Console,
staging, commit ou push. Próximo passo: FOUNDATION REVIEW V2.

## 14/09/2026 — WORKSPACE CONTENT FOUNDATION REMEDIATION IMPLEMENT V2 — COMPLETE / SEM COMMIT

Implementada exclusivamente a Remediation V2 local da Foundation. A cadeia
de autorização passou a exigir `RegisteredProfileHandle`,
`AuthorizedSubjectHandle` e `AuthorizedOperationContext` emitidos e
verificados por seus respectivos issuers; `ContentAuthProfile` e
`WorkspaceSubject` não são authorities. O broker é obrigatório tanto para a
normalização quanto para o `ContentReadTransport`.

Foram adicionadas a matriz fechada de capability/scope/subject/admin, os
resultados tipados `DriveSummary`/páginas Drive, enforcement de `max_items`,
rejeição segura de respostas excessivas, retry interno que nunca repete
400/401/403/404, ceilings absolutos de bytes/caracteres/chunks e client de
produção sem injeção pelo construtor público. Field masks, endpoints, método
GET, `trashed=false`, `corpora=drive` e parâmetros Shared Drive permanecem
internos e allowlistados.

A suíte direcionada passou em **84 testes** e a regressão completa em
**543 testes** (518 preexistentes preservados + 25 novos). Não foram criadas
tools Content ou Write; o catálogo permanece com 20 tools e `mcp.run()` segue
como operação final de `server.py`. Não houve chamadas Google/Drive/Gmail/
Docs/Sheets/Slides/MCP funcional, geração de token, DWD, IAM `signJwt`, ADC,
mudança de Cloud/Admin Console/IAM/DWD/scopes/Service Account, staging,
commit ou push.

Próximo passo: **FOUNDATION REVIEW V3**, mediante autorização explícita. O
Write Architecture/Safety Plan permanece preservado e a implementação Write
continua pausada.

## 14/09/2026 — WORKSPACE CONTENT FOUNDATION REVIEW V3 — BLOCKED

A revisão adversarial V3 preservada no roadmap encontrou sete pontos antes do
checkpoint: **FV3-P0-01** authority de issuer mutável/spoofable,
**FV3-P0-02** bypass de broker por subclass/duck typing, **FV3-P1-01** caminhos
de response/JSON genéricos, **FV3-P1-02** superfície de injeção de client de
teste, **FV3-P2-01** aceitação de `trashed=true` no resultado,
**FV3-P2-02** operação textual livre no safe error e **FV3-P3-01** cobertura
adversarial insuficiente. A Review não alterou arquivos nem executou atividade
Google.

## 14/09/2026 — WORKSPACE CONTENT FOUNDATION REMEDIATION PLAN V3 — COMPLETE

O plano V3 definiu um kernel de authority in-process lexicalmente encapsulado,
handles opacos sem dados, runtime selado, bootstrap separado, adapter HTTP por
operação, isolamento do client de testes, invariantes de resultado e enum
fechado para operações de erro. O threat model exclui comprometimento do
processo, monkeypatch irrestrito, debugger e alteração de closure cells; nenhuma
funcionalidade Google, MCP Content ou Write foi incluída.

## 14/09/2026 — WORKSPACE CONTENT FOUNDATION REMEDIATION IMPLEMENT V3 — COMPLETE / SEM COMMIT

Implementada exclusivamente a Remediation V3 local. O kernel closure-owned
emite e verifica, por identidade e por runtime, `RegisteredProfileHandle`,
`AuthorizedSubjectHandle` e `AuthorizedOperationContext` sem metadados de
authority nas instâncias. Fabricação por `object.__new__`, cópia, cópia profunda
e reutilização entre runtimes não concedem autoridade. Provisioning, resolução,
broker, normalização e adapter ficam capturados internamente pela fachada
`ContentRuntime.execute()`; o bootstrap de produção aceita zero parâmetros e
falha fechado enquanto não existir provisioning autorizado.

O transporte genérico anterior foi removido. O adapter realiza apenas os três
contratos Drive Foundation conhecidos, com GET/host/endpoint/query fixos,
tratamento seguro de status e parse direto para resultados tipados. Não há API
Content que devolva `httpx.Response`, headers, body ou JSON genérico, nem API
para anexar ou substituir client após a montagem. O parser de inventário aceita
somente `trashed is False`, e `ContentSafeError` usa `ContentErrorOperation`
fechado sem refletir identificador textual arbitrário.

Os testes direcionados passaram em **99 testes** e a regressão completa em
**558 testes**, preservando os 543 anteriores. O warning local conhecido do
cache pytest permaneceu sem impacto. O catálogo público continua com 20 tools,
Content com 0 e Write com 0; `mcp.run()` permanece a operação final de
`server.py`. Não houve chamadas Google/Drive/Gmail/Docs/Sheets/Slides/Directory
ou MCP funcional, token, DWD, IAM `signJwt`, ADC, mudança Cloud/Admin Console/
IAM/DWD/scopes/Service Account, staging, commit ou push.

Próximo passo: **FOUNDATION REVIEW V4**, mediante autorização explícita. O
Write Architecture/Safety Plan permanece preservado e a implementação Write
continua pausada.

## 14/09/2026 — WORKSPACE CONTENT FOUNDATION REVIEW V4 — BLOCKED

A revisão adversarial V4 encontrou seis pontos antes do checkpoint:
**FV4-P0-01** trust root/broker bypass, **FV4-P0-02** fabricação e
subclassificação de `ContentRuntime`, **FV4-P1-01** execução por adapter,
client e request normalizado arbitrários, **FV4-P2-01** bypass de subclasses em
limits/retry, **FV4-P2-02** canal textual em auditoria e **FV4-P3-01** cobertura
adversarial insuficiente. A Review não alterou arquivos nem executou atividade
Google.

## 14/09/2026 — WORKSPACE CONTENT FOUNDATION REMEDIATION PLAN V4 — COMPLETE

O plano definiu o threat model suportado — inputs MCP/runtime não confiáveis e
API Content suportada — e deixou execução Python arbitrária após comprometimento
do processo fora do escopo. A remediação selecionou startup composition root,
runtime concreto sem callable arbitrário, operações HTTP fechadas, normalized
data-only, validação de limites no consumo e enums de auditoria.

## 14/09/2026 — WORKSPACE CONTENT FOUNDATION REMEDIATION IMPLEMENT V4 — COMPLETE / SEM COMMIT

Implementada exclusivamente a Remediation V4 local. Foram removidos o
`_RUNTIME_SUBCLASS_TOKEN`, `_bind_content_runtime` e as fábricas module-level de
authority. O bootstrap passou a montar a cadeia completa em escopo lexical; o
runtime aceita somente requests tipados exatos e não expõe componentes,
executor, client ou setter.

O normalized request deixou de transportar endpoint, método ou query arbitrária.
O adapter usa host, path, GET, fields, invariantes e parsers derivados das
operações Drive fechadas. Policies de paginação, contexto e retry são
revalidadas no consumo; campos de operação de auditoria passaram a exigir
identificadores fechados; a boundary de resultados tipados e o invariant
`trashed is False` foram preservados.

A regressão local passou em **558 testes**. Não foram criadas tools Content ou
Write; o catálogo permanece com 20 tools e `mcp.run()` continua a operação
final de `server.py`. Não houve chamadas Google/Drive/Gmail/Docs/Sheets/Slides/
Directory/MCP funcional, token, DWD, IAM `signJwt`, ADC, alteração Cloud/Admin
Console/IAM/DWD/scopes/Service Account, staging, commit ou push.

Próximo passo: **FOUNDATION REVIEW V5**, mediante autorização explícita. O
Write Architecture/Safety Plan permanece preservado e a implementação Write
continua pausada.

## 14/09/2026 — WORKSPACE CONTENT FOUNDATION REVIEW V5 — PASS

A revisão independente e adversarial V5 confirmou que os findings relevantes
V1–V4 estão fechados sob o threat model aprovado: inputs MCP/runtime não
confiáveis e a API Content suportada. Não foram encontrados P0, P1 ou P2
bloqueante de checkpoint. A Foundation foi considerada **READY FOR CHECKPOINT**.

Foram confirmados: fachada `ContentRuntime` fechada, bootstrap sem parâmetros
de provisioning, operações Drive fechadas, request normalizado somente como
dados, adapter/client não injetável pela API suportada, limites e retry
revalidados no consumo, resultados tipados, invariant `trashed is False`,
categorias de auditoria fechadas, barreira somente leitura e isolamento da
camada Read histórica. A suíte direcionada passou em **99 testes** e a
regressão completa em **558 testes**. A Review não modificou arquivos e não
executou atividade Google.

## 14/09/2026 — WORKSPACE CONTENT FOUNDATION CHECKPOINT V1 — COMPLETE / CHECKPOINTED

Este commit registra exclusivamente o checkpoint da Fase 1.5.0 — Architecture
& Safety. O estado canônico passa a ser:

```text
Foundation Review V5       = PASS
open P0                    = 0
open P1                    = 0
checkpoint-blocking P2     = 0
1.5.0 Architecture & Safety = COMPLETE / CHECKPOINTED
1.5.1 Shared Drive Discovery = PENDING
```

O checkpoint não implementa tools Content MCP, autenticação Google real,
Shared Drive Discovery, Gmail ou Write. Content Research Service Account,
Content DWD, validação funcional Google e alterações de Cloud/Admin Console
continuam não executados. O threat model V4 permanece preservado: inputs MCP/
runtime não confiáveis e API Content suportada estão no escopo; execução Python
arbitrária pós-comprometimento, monkeypatch/introspecção pós-comprometimento,
debugger/memória e mutação deliberada de closures privadas estão fora do escopo.

O Write Architecture/Safety Plan permanece preservado e a implementação Write
continua pausada. O próximo estágio 1.5.1 exige autorização explícita separada.

## 15/09/2026 — WORKSPACE CONTENT 1.5.1 SHARED DRIVE DISCOVERY IMPLEMENT V1 — COMPLETE / SEM CHECKPOINT

O PLAN V1 aprovado foi implementado exclusivamente localmente com as tools
MCP `workspace_drives_list` e `workspace_drive_get`. O catálogo passou de 20
para 22 tools únicas: 20 Read históricas, 2 Content e 0 Write. A ferramenta
`workspace_drive_files_list` não foi implementada nem registrada; os contratos
internos correspondentes da Foundation foram preservados para 1.5.2.

As tools usam requests/resultados tipados da Foundation, endpoints HTTPS e GET
fixos da Drive API v3, fields allowlisted, uma página por chamada, caps de 100,
IDs operacionais estáveis, nomes duplicados preservados e admin mode opt-in
default false. O header de autorização é aplicado somente dentro do adapter.
Foi adicionada estrutura local de configuração Content sem e-mail real da
futura SA e provider keyless com ports injetáveis apenas por fakes, cache RAM,
expiry bounded e redaction segura.

Testes locais cobrem schemas MCP estritos, catálogo/duplicatas, paginação,
limites, IDs/path segments, admin authorization, allowlists, erros, token/JWT/
credential redaction, mutation barrier e regressão da Read Layer. A suíte final
passou em **629 testes** (558 baseline + 71 novos), sem falhas. A execução
não fez chamadas Google, Drive, ADC, IAM `signJwt`, DWD, OAuth ou Admin/Cloud;
nenhuma configuração externa foi alterada. `REAL VALIDATION = NOT STARTED`.
Não houve staging, commit ou push; o checkpoint da Foundation
`564a47e092c29424131045a37527350c2d2c9619` foi preservado.

## 15/09/2026 — WORKSPACE CONTENT 1.5.1 OPERATIONAL AUTH BINDING IMPLEMENT V1 — COMPLETE / SEM CHECKPOINT

Implementado exclusivamente localmente o binding configurável da identidade
Content: variáveis process-only não secretas, `ContentAuthProfile`, subject
fixo, adapters lazy para ADC/IAM/OAuth e integração com o
`KeylessContentTokenProvider`. O scope permaneceu fechado em
`https://www.googleapis.com/auth/drive.readonly`; não foi criada variável de
scope nem configurado Client ID no runtime. `customer_id` é obrigatório e não
há fallback para `my_customer`.

O Content Research Service Account, IAM Token Creator e DWD `drive.readonly`
foram **MANUALLY CONFIGURED**, conforme confirmação do operador, mas não foram
verificados por chamadas reais. ADC não foi consultada e a REAL VALIDATION não
foi iniciada. O customer ID ainda deve ser fornecido antes da RV1.

Os testes adicionados usam somente fakes e `httpx.MockTransport` para ADC,
IAM, OAuth e Drive. A suíte passou em **652 testes**, sem falhas, preservando
os 629 testes anteriores. Não houve alteração em Cloud/Admin Console, staging,
commit ou push.

## 15/09/2026 — WORKSPACE CONTENT 1.5.1 SHARED DRIVE DISCOVERY — RV1 / DIAGNOSTIC V1 / RV2 / FINAL REVIEW V1

RV1 preserva o precheck `CONFIG` falho e **zero operações funcionais Google**:
o caminho direto Python/PowerShell estava fora do ambiente próprio da instância
MCP. Diagnostic V1 confirmou `config.toml`, a tabela MCP `env`, o parse de
`ContentConfig`, o provisioning do profile e a construção do subject; nenhuma
variável, valor sensível ou configuração Google foi exposta ou alterada.

RV2 passou exclusivamente pelo MCP hospedado com exatamente uma chamada
`workspace_drives_list` limitada e `use_domain_admin_access=false`. A cadeia
CONFIG → ADC → IAM `signJwt` → DWD OAuth → Drive API passou; o registro seguro
é: uma página com um Shared Drive, próxima página presente, zero retries, zero
continuação, zero mutações e zero exposição sensível. IDs, nomes, token de
próxima página, JWT, Authorization, resposta OAuth, ADC e payload Drive não
foram registrados.

FINAL REVIEW V1 = **PASS**. Os testes locais confirmaram 71 casos Shared
Drive/keyless, 23 de binding operacional, 207 de Foundation/protocolo e
**652 passed** na regressão completa. A revisão confirmou catálogo único de 22
tools (20 Read, 2 Content, 0 Write), ausência de
`workspace_drive_files_list`, isolamento semântico da camada Read e ausência
de credenciais reais no diff/repositório. Documentação sincronizada; staging,
commit e push permanecem vazios/zero. Próximo gate: **CHECKPOINT somente com
autorização explícita**.

## 15/09/2026 — WORKSPACE CONTENT 1.5.1 SHARED DRIVE DISCOVERY — CHECKPOINT V1 — COMPLETE / THIS COMMIT

Este commit consolida exclusivamente o diff autorizado de 1.5.1 desde o
checkpoint baseline `564a47e092c29424131045a37527350c2d2c9619`: Shared Drive
Discovery, configuração operacional Content, binding keyless de produção,
registro MCP, testes e documentação. O commit usa a mensagem
`feat: add shared drive discovery`; o hash canônico é informado no relatório
pós-commit, sem criar um segundo commit documental.

O gate final confirmou 20 arquivos autorizados e zero unrelated, catálogo com
22 tools únicas (20 Read, 2 Content, 0 Write), scope Content somente
`drive.readonly`, ausência de credenciais reais e **652 testes aprovados**. A
RV2 permanece preservada como uma única chamada MCP hospedada; este checkpoint
não executou Google, Drive, ADC, IAM `signJwt` ou OAuth. Não houve push e 1.5.2
não foi iniciada.

## 15/09/2026 — WORKSPACE CONTENT 1.5.2 DRIVE FILE INVENTORY IMPLEMENT V1 — COMPLETE / SEM CHECKPOINT

Implementado exclusivamente o PLAN V1 aprovado de Drive File Inventory. Foi
adicionada uma única tool MCP, `workspace_drive_files_list`, com contrato
fechado de `drive_id`, `page_size`, `page_token` e `max_items`. O catálogo
passou a 23 tools únicas: 20 Read, 3 Content e 0 Write; as 20 tools Read
permaneceram semanticamente inalteradas.

O adapter emite no máximo um `GET` para o endpoint fixo Drive `files.list`, com
corpus, drive, space, Shared Drive flags, fields e `trashed = false` fixos. O
hard cap Content é 500. O parser fail-closed exige `trashed is False`, valida
size int64 não negativa, preserva folders e MIME types e produz somente o DTO
allowlisted; nenhum conteúdo, link, permission, owner ou resposta bruta é
exposto.

A regra interna histórica `DRIVE_METADATA / drive.metadata.readonly` foi
alinhada ao profile produtivo já validado `DRIVE_DISCOVERY / drive.readonly`.
Não houve novo scope, DWD, variável, Service Account, IAM ou configuração
Google. A suíte dedicada passou em 94 casos e a regressão completa em **747
passed**, somente com mocks/fakes. Google activity = 0, ADC activity = 0,
staging = empty, commit = 0 e push = 0. PLAN V1 e IMPLEMENT V1 estão completos;
REAL VALIDATION permanece **NOT STARTED** e depende de autorização explícita.

## 16/09/2026 — WORKSPACE CONTENT 1.5.2 DRIVE FILE INVENTORY — REAL VALIDATION RV1 / RV2

RV1 foi encerrada sem chamadas funcionais porque a instância hospedada ainda
apresentava catálogo stale: 22 tools, `workspace_drive_files_list` ausente,
classificação `MCP_TRANSPORT_OR_CATALOG`.

Após nova instância MCP, RV2 confirmou catálogo fresco com 23 tools únicas (20
Read, 3 Content, 0 Write). Foram executadas exatamente duas chamadas MCP:
`workspace_drives_list` retornou um Drive e token de continuação presente;
`workspace_drive_files_list` retornou um arquivo e token presente. O invariant
`trashed=false` passou pelo parser. Não houve retry, continuação, mutação ou
exposição de valores sensíveis. Google activity adicional, ADC, IAM e OAuth = 0.

## 16/09/2026 — WORKSPACE CONTENT 1.5.2 DRIVE FILE INVENTORY — FINAL REVIEW V1 — COMPLETE / SEM CHECKPOINT

O diff integral do IMPLEMENT V1 foi revisado: somente source, testes e
documentação autorizados. O contrato público, DTO, request fixo, cap 500,
validações, profile `DRIVE_DISCOVERY` / `drive.readonly`, segurança keyless,
ausência de admin mode, auditoria, isolamento Read e boundary MCP passaram.

A suíte dedicada passou em 94 casos e a regressão completa em **747 passed**.
O catálogo permanece 23/20/3/0 sem duplicatas. FINAL REVIEW V1 = **COMPLETE**;
CHECKPOINT V1 = **COMPLETE / THIS COMMIT**. Não houve nova chamada externa nesta
revisão; o SHA do commit é registrado somente pelo Git após a consolidação.

## 16/09/2026 — WORKSPACE CONTENT 1.5.3 CONTENT READING ARCHITECTURE & SAFETY — IMPLEMENT V1 — COMPLETE / SEM VALIDAÇÃO

Implementado exclusivamente o substrate arquitetural comum aprovado no PLAN
V1. A entrega adicionou routing MIME fechado, budgets imutáveis e finitos,
`InventorySnapshot`, preflight interno de download, `ContentChunk` com payloads
tipados, variantes de provenance, taxonomia fechada de processing outcomes,
semântica de continuação para limites e o protocolo interno `ContentReader`.

O invariant de cobertura exige exatamente um outcome terminal por arquivo;
`PARTIALLY_PROCESSED` representa limite recuperável com continuação opaca e
`TOO_LARGE` representa limite absoluto ou continuação impossível. Conteúdo é
untrusted data e `NEVER_EXECUTE_FILE_CONTENT` permanece testável. Nenhum reader
concreto, parser, endpoint, MCP tool, scope, dependência, mutation route ou
alteração de Read Layer foi introduzido.

Foram adicionados somente testes locais sintéticos para routing, budgets,
chunks, provenance, outcomes, preflight, safety e boundary (**80 targeted;
827 regression**). Não houve Google
API, ADC, IAM, OAuth, instalação de pacote, staging, commit ou push nesta
entrega; a REAL VALIDATION permanece **NOT STARTED** e aguarda autorização
explícita.

## 16/09/2026 — WORKSPACE CONTENT 1.5.3 CONTENT READING ARCHITECTURE & SAFETY — FINAL REVIEW V1 — COMPLETE / SEM RV GOOGLE

A revisão local confirmou os 19 caminhos autorizados, exports intencionais do
substrate, routing MIME fechado, cobertura exatamente-um-outcome, budgets
finitos, continuação parcial segura, payloads tipados, provenance, snapshot
TOCTOU, preflight interno, ausência de conteúdo ativo, erros seguros,
isolamento de auth/Read/Write e catálogo 23/20/3/0 sem duplicatas.

A reconciliação de testes registrou **207 passed** com o comando explícito
`test_content_auth_boundary.py` + `test_content_foundation.py` +
`test_content_transport_security.py` + `test_mcp_protocol.py`. O relatório de
IMPLEMENT havia executado somente os três últimos arquivos (**187 passed**),
logo a diferença é exclusivamente os 20 casos de `test_content_auth_boundary.py`;
nenhum teste foi deletado, renomeado, movido, desabilitado ou perdido. A
regressão completa permanece em **827 passed**.

FINAL REVIEW V1 = **COMPLETE**. Como não há reader concreto, endpoint ou tool
Content executável em 1.5.3, REAL VALIDATION Google = **NOT APPLICABLE / NOT
EXECUTED**. Não houve alteração de código/teste nesta revisão, atividade
Google/ADC/IAM/OAuth, staging, commit ou push; 1.5.3 CHECKPOINT V1 foi
autorizado para consolidação neste change set.

## 16/09/2026 — WORKSPACE CONTENT 1.5.3 CONTENT READING ARCHITECTURE & SAFETY — CHECKPOINT V1 — COMPLETE

O checkpoint consolida exclusivamente os 19 paths autorizados do substrate
comum de Content Reading, seus testes locais e a documentação sincronizada.
Routing MIME, budgets finitos, coverage/outcomes, chunks, provenance,
snapshot/preflight, safety e protocolo interno permanecem sem readers
concretos, novas MCP tools, scopes, dependências, mutações ou alterações da
Read Layer. O estado final é PLAN V1 = COMPLETE, IMPLEMENT V1 = COMPLETE,
REAL GOOGLE VALIDATION = NOT APPLICABLE, FINAL REVIEW V1 = PASS e CHECKPOINT
V1 = COMPLETE. O SHA é produzido somente pelo Git após a consolidação.

## 16/09/2026 — WORKSPACE CONTENT 1.5.4 GOOGLE DOCS CONTENT — IMPLEMENT V1 — COMPLETE

Implementado o primeiro reader concreto de Content por meio da façade pública
`workspace_file_content_read`, com routing MIME fechado e suporte concreto
exclusivo a `application/vnd.google-apps.document`. As demais classes já
roteadas continuam produzindo outcome explícito de reader indisponível, sem
simular cobertura.

O fluxo Google Docs usa adapter fechado para `documents.get`, com
`includeTabsContent=true`, `suggestionsViewMode=SUGGESTIONS_INLINE`, comentários
fora do escopo e resposta limitada a 32 MiB durante a leitura. O guard TOCTOU
usa `files.get` metadata-only antes e depois da leitura, validando `id`,
`mimeType`, `modifiedTime` e `trashed` antes de liberar qualquer chunk.

A extração cobre tabs e child tabs em depth-first pre-order, títulos de tabs,
body, parágrafos, text runs, headings, listas, tabelas aninhadas, TOC, headers,
footers, footnotes e texto visível de links, person/date/rich-link e alt text.
Objetos visuais, equações e unions potencialmente textuais não suportadas
produzem partial terminal explícito. Limite de output produz partial resumível
com continuação opaca, íntegra, expiring, vinculada a arquivo, MIME, snapshot e
versão do reader.

Foi adicionada a capability semântica interna `GOOGLE_DOCS_CONTENT`, reutilizando
exclusivamente `drive.readonly`: novos scopes OAuth = 0, nova autorização DWD =
0, IAM/Service Account/env novos = 0. `canDownload`, export, OCR, comments
Developer Preview e qualquer operação Write permanecem ausentes.

PLAN V1 = **COMPLETE** e IMPLEMENT V1 = **COMPLETE**. REAL VALIDATION = **NOT
EXECUTED**, FINAL REVIEW/CHECKPOINT = **NOT EXECUTED**. O serviço
`docs.googleapis.com` precisa estar habilitado para a validação real, mas o
estado atual permanece **UNKNOWN** e qualquer ação futura será manual e
explicitamente autorizada. Não houve chamada Google funcional, ADC, IAM,
OAuth, gcloud, staging, commit ou push nesta entrega.

Os gates locais registraram **33 passed** no reader Google Docs, **84 passed**
no substrate 1.5.3, **172 passed** em Shared Drive + Drive Inventory +
Operational Auth, **207 passed** em Foundation/security/protocol e **864
passed** na regressão completa, acima do baseline anterior de 827 sem
regressões.

## 16/09/2026 — WORKSPACE CONTENT 1.5.4 GOOGLE DOCS CONTENT — PRE-RV REVIEW V1 — BLOCKED

A revisão local pré-RV bloqueou a autorização de acesso real por seis findings:
descompressão transparente antes do contador de bytes, outcomes de falha que
aceitavam contagens/chunks, store de continuation sem sincronização, HTTP 408
classificado incorretamente após retries, `sectionBreak` descartado e cobertura
de testes insuficiente. A revisão não alterou arquivos e não executou atividade
Google, ADC, IAM, OAuth ou gcloud.

## 16/09/2026 — WORKSPACE CONTENT 1.5.4 GOOGLE DOCS CONTENT — PRE-RV REMEDIATION V1 — COMPLETE

Os seis findings foram corrigidos sem ampliar a superfície MCP. O adapter agora
conta o stream raw/Content-Encoding por `iter_raw()`, aplica cap raw/wire de 32
MiB, decodifica somente `identity`, `gzip` e `deflate` incrementalmente com cap
decodificado de 32 MiB e trata `Content-Length` apenas como otimização. Bombas
de compressão e encodings desconhecidos falham fechados sem retry de
`TOO_LARGE`.

Failures terminais exigem zero chunks/resultados/continuation; o store local de
continuation tornou purge/capacity/insertion/resolve/expiry atômicos e continua
limitado a 1.000 estados, TTL máximo de uma hora e valores tipados sem conteúdo.
HTTP 408 termina como `TRANSIENT_UPSTREAM` após no máximo três attempts.
`sectionBreak` passou a produzir `structural_locations` bounded com provenance
tipada, location-only, incluindo tab, segmento, structural path, índices e
relações seguras de header/footer, sem texto inventado ou novo fetch.

Os testes locais registraram **20 casos específicos de remediação**, **46
Google Docs**, **91 substrate**, **54 Shared Drive**, **94 Drive Inventory**,
**24 Operational Auth**, **207 Foundation/security/protocol** e **884 passed**
na regressão completa. PRE-RV REVIEW V1 permanece **BLOCKED** historicamente;
PRE-RV REMEDIATION V1 = **COMPLETE**; PRE-RV re-review, REAL VALIDATION e
CHECKPOINT = **NOT EXECUTED**. Não houve Google, ADC, IAM, OAuth, gcloud,
staging, commit ou push.

## 16/09/2026 — WORKSPACE CONTENT 1.5.4 GOOGLE DOCS CONTENT — PRE-RV REMEDIATION V2 — COMPLETE

A continuação recuperou o working tree interrompido sem reiniciar ou refazer a
remediação. Branch, HEAD, staging e os 27 paths autorizados foram reconfirmados;
os seis findings permanecem resolvidos. A evidência adicional de
`sectionBreak` confirmou também documento sem texto como `EMPTY`, com boundary
location-only no array bounded `structural_locations` e sem texto inventado.

Os gates finais passaram em **21 casos específicos de remediação**, **47 Google
Docs**, **91 substrate**, **54 Shared Drive**, **94 Drive Inventory**, **24
Operational Auth**, **207 Foundation/security/protocol** e **885 testes** na
regressão completa. PRE-RV REVIEW V1 continua historicamente **BLOCKED**;
PRE-RV REMEDIATION V1/V2 = **COMPLETE**; PRE-RV RE-REVIEW, REAL VALIDATION e
CHECKPOINT = **NOT EXECUTED**. Próximo gate: autorização explícita de PRE-RV
RE-REVIEW. Google, ADC, IAM, OAuth, gcloud, staging, commit e push permaneceram
zero.

## 16/09/2026 — WORKSPACE CONTENT 1.5.4 GOOGLE DOCS CONTENT — PRE-RV RE-REVIEW V1 — BLOCKED / RR-P2-01 REMEDIATION V1 — COMPLETE

O PRE-RV RE-REVIEW V1 manteve o gate bloqueado exclusivamente pelo finding
RR-P2-01: o decoder já estava tecnicamente bounded e fail-closed, mas faltavam
testes versionados permanentes para streams gzip/deflate malformados,
truncados e com trailing data, Content-Encoding empilhado e o raw cap + 1
exato.

RR-P2-01 REMEDIATION V1 adicionou somente testes em
`tests/test_google_docs_content.py`; nenhum source de produção mudou. Os testes
atravessam o stream raw real, a seleção de encoding, o decoder incremental, as
validações de EOF/trailing, os caps e o resultado seguro. Foram aprovados **12
casos RR-P2-01**, **21 casos de remediação anteriores**, **59 Google Docs**,
**91 substrate**, **54 Shared Drive**, **94 Drive Inventory**, **24 Operational
Auth**, **207 Foundation/security/protocol** e **897 testes** na regressão
completa. O compression-bomb existente permaneceu inalterado e aprovado.

PRE-RV REVIEW V1 continua historicamente **BLOCKED — 6 findings**; PRE-RV
REMEDIATION V1/V2 = **COMPLETE**; PRE-RV RE-REVIEW V1 = **BLOCKED — RR-P2-01**;
RR-P2-01 REMEDIATION V1 = **COMPLETE**; PRE-RV FINAL RE-REVIEW, REAL VALIDATION
e CHECKPOINT = **NOT EXECUTED**. Próximo gate: autorização explícita de PRE-RV
FINAL RE-REVIEW. Google, ADC, IAM, OAuth, gcloud, staging, commit e push
permaneceram zero.

## 17/09/2026 — WORKSPACE CONTENT 1.5.4 GOOGLE DOCS — FAILURE OBSERVABILITY IMPLEMENT V1 — COMPLETE / SEM COMMIT

A implementação autorizada adicionou o enum fechado `FailureStage` com dez
estágios causais e propagou `failure_stage` tipado no `ProcessingOutcome`, nos
boundaries do reader Google Docs e na serialização MCP. `processing_status`,
`safe_error_code`, budgets, retry, scopes, capability routing e invariantes de
outcome permaneceram inalterados. O audit de conteúdo aceita somente
`FailureStage` ou `null`, preservando pseudonimização HMAC e sem conteúdo,
identificadores, URLs, mensagens de exceção ou material de credencial.

Foram adicionados testes sintéticos de preflight, request/resposta Docs,
transporte, JSON/schema, extração estrutural, provenance, postflight,
serialização MCP e leakage. O catálogo permaneceu em 24 tools (20 Read, 4
Content, 0 Write), sem scopes, DWD, IAM, configuração ou dependências novas.
PRE-RV FINAL RE-REVIEW V1 = **PASS** é o estado histórico corrigido; a cadeia
de real auth e target resolution permanece **PASS**, a V1 de validação real
teve metodologia de captura insuficiente, V2 produziu `EXTRACTION_FAILED`, o
diagnóstico foi concluído e a validação real pós-remediação permanece
**PENDING**. Implementação validada somente localmente, sem Google, ADC, IAM,
OAuth, staging, commit ou push.

## 17/09/2026 — WORKSPACE CONTENT 1.5.4 GOOGLE DOCS — FAILURE OBSERVABILITY REMEDIATION V2 — COMPLETE / SEM COMMIT

A remediation V2 corrigiu exclusivamente os dois achados P2 do PRE-REAL
OBSERVABILITY REVIEW V1. `README.md` e `docs/02_MCP_CATALOG.md` passaram a
registrar o estado factual: PRE-RV FINAL RE-REVIEW V1 = PASS, real auth,
discovery e target resolution = PASS, REAL CONTENT VALIDATION V2 bloqueada por
`EXTRACTION_FAILED`, observabilidade implementada e validada localmente, e
validação real de conteúdo pós-remediação ainda pendente.

Os testes existentes de auditoria e protocolo MCP agora exercitam todos os
cinco sentinelas sintéticos nos boundaries de audit e exceção segura, provando
que não atravessam a representação pública. Não houve mudança funcional de
produção, nem alteração de scopes, DWD, IAM, configuração, catálogo ou
dependências. Google, ADC, IAM, OAuth, staging, commit, push e checkpoint
permaneceram zero.

## 17/09/2026 — WORKSPACE CONTENT 1.5.4 GOOGLE DOCS — OBSERVABILITY REMEDIATION V3 — COMPLETE / SEM COMMIT

A Remediation V3 corrigiu exclusivamente o P2-02 remanescente do PRE-REAL
OBSERVABILITY RE-REVIEW V2: a evidência de teste pública/MCP agora injeta cada
um dos cinco sentinelas em uma exceção upstream sintética levantada pelo
`httpx.MockTransport`, deixa o adapter existente realizar a tradução segura e
atravessa o boundary MCP real até `TextContent` e JSON. O teste parametrizado
confirma a presença positiva dos valores na mensagem, no `repr` e no traceback
antes da tradução; depois confirma a ausência de todos os sentinelas, da
mensagem, do `repr` e do traceback nos envelopes público e MCP, preservando os
campos seguros de status, código e estágio.

Os caminhos audit e exception existentes permaneceram inalterados e continuam
em 5/5. A cobertura public e MCP passou a 5/5; a força adversarial passou a
**STRONG**, sem leakage. Nenhum source funcional foi alterado. Os testes locais
foram executados sem Google, ADC, IAM, OAuth ou chamadas funcionais; a revisão
pós-remediação, a validação real de conteúdo e o checkpoint permanecem
pendentes. 1.5.4 continua **NOT COMPLETE**.

## 18/09/2026 — WORKSPACE CONTENT 1.5.4 GOOGLE DOCS — STRUCTURAL RUNTIME FINGERPRINT IMPLEMENT V1 — COMPLETE / SEM COMMIT

Implementada exclusivamente a observabilidade estrutural autorizada para a
falha real pendente. `StructuralFailureKind` é uma taxonomia fechada de onze
valores e percorre `ContentSafeError`, `ProcessingOutcome`, a serialização
pública e o boundary MCP `TextContent` JSON. O fingerprint é `null` fora de
`DOCS_STRUCTURAL_EXTRACTION`; dentro desse stage, outcomes sem fingerprint e
combinações inválidas falham fechado. Nenhuma string arbitrária de caller,
resposta upstream ou conteúdo de documento é aceita como fingerprint.

Foram etiquetados de modo causal tabs, dispatch do body, parágrafos,
índices/ranges de elementos de parágrafo, tabelas, células, TOC, headers,
footers, footnotes e validação estrutural residual. `PROVENANCE_BUILD` foi
mantido isolado com `structural_failure_kind=null`; `content/audit.py` não foi
alterado, conforme o PLAN. `processing_status`, `safe_error_code` e
`failure_stage` preservam integralmente seu significado anterior.

Os testes locais sintéticos atravessam cada uma das onze fronteiras reais,
propagation, estados nulos, combinações inválidas, resultado público,
serialização MCP e leakage adversarial de material sintético de documento, URL
e identificador. O hardening adicional confirma que um primeiro `sectionBreak`
com `endIndex=1` sem `startIndex`, e o caso explícito `startIndex=0`, extraem
com sucesso; a hipótese sectionBreak como causa da falha real foi
**REJEITADA**. Isto não implementa correção funcional de parser.

Os gates focais registraram 12 testes de fingerprint causal/propagation, 1 de
serialização MCP, 1 de leakage e 2 de sectionBreak; a regressão completa
terminou em **927 passed**.

REAL CONTENT VALIDATION V3 permanece **BLOCKED / DOCS_STRUCTURAL_EXTRACTION**;
a próxima leitura real continua pendente, bem como review final e checkpoint.
Não houve Google, Drive, Docs, ADC, IAM, OAuth, login, mudanças de scopes/DWD/
IAM/configuração, staging, commit ou push. 1.5.4 permanece **NOT COMPLETE**.

## 18/09/2026 — WORKSPACE CONTENT 1.5.4 GOOGLE DOCS — PARAGRAPH RUNTIME FINGERPRINT IMPLEMENT V1 — COMPLETE / SEM COMMIT

Implementada exclusivamente a dimensão de observabilidade aprovada para a
falha real `PARAGRAPH_STRUCTURE`. O enum fechado `ParagraphFailureKind` possui
oito valores e foi propagado por `ContentSafeError`, `ProcessingOutcome`, o
resultado público e o boundary MCP `TextContent` JSON. O nesting invariant
exige que o campo só exista com `DOCS_STRUCTURAL_EXTRACTION` e
`StructuralFailureKind.PARAGRAPH_STRUCTURE`; índices de `ParagraphElement`,
provenance e demais boundaries permanecem isolados.

Os testes locais atravessam causalmente os oito boundaries, preservam a
classificação filha, cobrem estados nulos e combinações inválidas e verificam
leakage público/MCP. A semântica funcional do parser não foi alterada,
`content/audit.py` não foi tocado, o catálogo continua 24/20/4/0 e a próxima
validação real de parágrafo permanece pendente. Não houve Google, ADC, IAM,
OAuth, login, mudança de scopes/DWD/configuração, staging, commit ou push.

## 20/09/2026 — WORKSPACE CONTENT 1.5.4 — ELEMENT STRUCTURE TARGETED DIAGNOSTIC V1 — COMPLETE / SEM CHECKPOINT

O histórico imutável da sequência foi reconciliado sem apagar falhas: REAL
V4B registrou `PARAGRAPH_STRUCTURE`; a implementação/revisão de
`ParagraphFailureKind` concluiu localmente com **946 passed**. A V5 inicial
encontrou `WSAEACCES` 10013 no ambiente Codex e `ADC_REFRESH` no MCP
hospedado. A classificação de sentinela fixa foi `REAUTH_REQUIRED`; a rede do
host manual permaneceu saudável. Após o operador executar `gcloud auth
application-default login`, a validação isolada da ADC passou e um processo MCP
novo confirmou a recuperação fim a fim da cadeia hospedada, sem registrar
credenciais.

A V5B tentou resolução global e foi bloqueada após 246 inventários e 24.500
itens, sem leitura de conteúdo. A V4 recusou repetir essa varredura. A estratégia
rasa posterior retornou 17 Shared Drives e resolveu o alvo após três primeiras
páginas, com 1.079 itens. A V5C consumiu o snapshot preservado em exatamente
uma leitura real e obteve `RESPONSE_VALIDATION`,
`DOCS_STRUCTURAL_EXTRACTION`, `PARAGRAPH_STRUCTURE` e
`ELEMENT_STRUCTURE`, com zero chunks e sem continuação. O fingerprint foi
decisivo, mas não identifica sozinho qual dos checks internos do único boundary
de elemento falhou.

Esta entrega adiciona somente scaffolding privado ao parser: um coletor
context-local, efêmero, desligado por padrão e first-failure-only. Quando um
harness futuro e explicitamente autorizado o instala, ele captura uma única
observação fechada: tipos simbólicos de índices/payload, flags de presença dos
metadados reconhecidos, members de union allowlisted, flag de desconhecido,
member selecionado e label interno fechado do branch que rejeitou. Não retém
texto, valores, chaves arbitrárias, URLs, e-mails, IDs, JSON bruto nem produz
logs, arquivos, auditoria ou campos MCP. A tool pública, requests, results,
enums, códigos seguros, scopes e arquitetura `ADC → IAM signJwt → DWD → OAuth`
permanecem inalterados.

Os testes focados cobrem seleção de union, payloads de `textRun`, variantes
não textuais, isolamento disabled-by-default, preservação de
`PARAGRAPH_ELEMENT_INDEX`, `ELEMENTS_CONTAINER` e `PARAGRAPH_LIMIT`, além de
leakage com sentinelas. A remediação funcional permanece pendente de uma única
observação real sanitizada. Os testes focados registraram **338 passed** e a
regressão completa **978 passed**, acima do baseline de 946. Não houve chamadas
Google/Drive/Docs, ADC, IAM, DWD, OAuth, rede, login, staging, commit, push ou
checkpoint nesta entrega.

## 20/09/2026 — WORKSPACE CONTENT 1.5.4 — TEXT RUN CONTENT STATE DIAGNOSTIC IMPLEMENTATION V1 — COMPLETE / SEM CHECKPOINT

A leitura real controlada, autorizada em gate separado, reduziu a falha de
`ELEMENT_STRUCTURE` a `TEXT_RUN_CONTENT_INVALID`. A observação privada mostrou
um `ParagraphElement` mapping com uma única union reconhecida (`textRun`),
payload mapping, índices presentes inteiros e ausência de chaves desconhecidas.
O valor de `textRun.content` não foi capturado nem exposto.

O plano local posterior confirmou que a implementação atual usa
`text_run.get("content")`: ausência e `null` ainda compartilham o mesmo caminho
de rejeição, enquanto tipos não string continuam inválidos. A evidência oficial
disponível torna ausência e `null` plausíveis, mas não prova uma normalização
segura sem conhecer a representação real e sua compatibilidade com os índices
UTF-16. Por isso, esta entrega mantém a semântica de produção e acrescenta
somente a classificação privada, fechada e sem valores `content_state`:
`ABSENT`, `NULL`, `STRING`, `BOOLEAN`, `INTEGER`, `FLOAT`, `MAPPING`, `LIST` ou
`OTHER_SCALAR`.

O novo campo só é preenchido imediatamente no branch
`TEXT_RUN_CONTENT_INVALID`; ele diferencia explicitamente chave ausente de
`null`, classifica `bool` antes de `int`, conserva uma única observação por
request e não é incluído em resultado, auditoria, logs, arquivo, banco, schema
ou tool MCP. A aceitação de `textRun.content`, os códigos seguros, os
fingerprints públicos, o catálogo e a arquitetura de autenticação permanecem
inalterados. Os testes focados registraram **139 passed** e a regressão
completa **996 passed**, sem falhas e acima do baseline de 978. O diagnóstico
real de estado de conteúdo permanece pendente de autorização explícita; não
houve Google, Drive, Docs, rede, ADC, IAM, DWD, OAuth, login, staging, commit,
push ou checkpoint nesta entrega.

## 20/09/2026 — WORKSPACE CONTENT 1.5.4 — GOOGLE DOCS TEXT RUN STRING FAILURE DIAGNOSTIC IMPLEMENTATION V1 — COMPLETE / SEM CHECKPOINT

A reassessment partiu da evidência real preservada
`TEXT_RUN_CONTENT_INVALID / content_state=STRING`: U+E907 e caracteres
private-use são aceitos, a comparação de span UTF-16 permanece isolada e a
causa real ainda é desconhecida. A implementação acrescenta somente o campo
privado `string_failure_reason`, um `Literal` fechado aos três predicados reais
de `_text()`: `MAXIMUM_EXCEEDED`, `UTF8_ENCODING_INVALID` e
`DISALLOWED_C0_OR_C1_CONTROL`. Cada motivo é capturado no ponto exato de
rejeição, na mesma observação first-failure-only, e somente para conteúdo
string. Não há fallback `OTHER`, retenção de texto/comprimento/Unicode/posição/
bytes/hash/erro, captura sem coletor, ou mudança de limite, UTF-8, controles,
U+E907, índice, outcome ou superfície MCP.

Os testes locais confirmam as três causas sintéticas, C0/C1, conteúdo válido,
TAB/LF/CR, U+E907 como placeholder após validação UTF-16, private-use, format,
noncharacter, Unicode suplementar, mismatch separado, ausência de leakage,
first-failure e equivalência de outcomes com o coletor instalado/desligado.
Foram **156 testes focados** e **1013 testes de regressão**, sem falhas e acima
do baseline de 996. O catálogo permaneceu em 24 tools (20 Read, 4 Content,
0 Write), sem duplicatas; `server.py` permaneceu inalterado por este gate.

O próximo gate recomendado é `GOOGLE_DOCS_TEXT_RUN_STRING_FAILURE_TARGETED_REAL_DIAGNOSTIC_V1`,
autorizado separadamente para uma leitura real controlada, retornando somente
branch, `content_state`, um dos três motivos e status seguros existentes. Nenhuma
chamada Google, Workspace MCP, rede ou autenticação ocorreu nesta entrega;
nenhum login ADC adicional nem `gcloud auth login` foi necessário ou executado.
Staging, commit e push = zero; checkpoint não autorizado. A causa real
`string_failure_reason` permanece desconhecida e 1.5.4 segue incompleta.

## 20/09/2026 — WORKSPACE CONTENT 1.5.4 — GOOGLE DOCS TEXT RUN CONTROL RANGE DIAGNOSTIC IMPLEMENTATION V1 — COMPLETE / SEM CHECKPOINT

A leitura real V1B resolveu a causa da falha do alvo como
`TEXT_RUN_CONTENT_INVALID / content_state=STRING /
DISALLOWED_C0_OR_C1_CONTROL`. `MAXIMUM_EXCEEDED` e
`UTF8_ENCODING_INVALID` foram eliminados para esse alvo. O plano de controle
V1 rastreou a política atual e concluiu que regras `InsertTextRequest` são de
inserção, não uma especificação de validade de respostas `TextRun`; U+E907
reforça essa distinção. Nenhuma classe atualmente rejeitada foi provada como
legítima em respostas por evidência estática, portanto nenhuma remediação foi
feita nem autorizada por inferência.

A observação privada, context-local, first-failure-only e desativada sem
coletor agora inclui `control_range`, com exatamente seis labels:
`C0_0000_0008`, `VT_000B`, `FF_000C`, `C0_000E_001F`, `DEL_007F` e
`C1_0080_009F`. A classificação ocorre no branch que já rejeita o primeiro
controle. A política de produção permanece idêntica: TAB/LF/CR continuam
aceitos e as seis classes continuam rejeitadas. Nenhum code point/caractere,
texto, posição, contagem ou fallback `OTHER`/`UNKNOWN` é retido; demais
callers de `_text`, limite, UTF-8, U+E907, validação UTF-16, proveniência,
chunking e resultados não mudaram.

Os testes focados registraram **183 passed**; a regressão completa registrou
**1040 passed**, sem falhas e acima do baseline de 1013. Pytest emitiu um aviso
na primeira execução com o cache padrão; a validação final pelo comando do
runbook com cache desativado passou sem warnings. O catálogo permaneceu em 24
tools (20 Read, 4 Content, 0 Write), sem duplicatas;
`server.py` não recebeu mudanças por este gate e `mcp.run()` segue como operação
final absoluta. As alterações preexistentes foram preservadas: 27 caminhos no
total, nenhum staging, commit ou push. Não houve Google, Drive, Docs,
Workspace MCP, rede ou autenticação; nenhum login adicional foi necessário ou
executado. Docs/04 e docs/05 estão sincronizados; 1.5.4 segue incompleta.

Próximo gate recomendado, não executado: `GOOGLE_DOCS_TEXT_RUN_CONTROL_RANGE_TARGETED_REAL_DIAGNOSTIC_V1`,
com autorização separada e no máximo uma leitura real controlada. A faixa real
do controle permanece desconhecida.

## 21/09/2026 — WORKSPACE CONTENT 1.5.4 — GOOGLE DOCS TEXT RUN VT TARGETED IMPLEMENTATION V1 — COMPLETE / SEM CHECKPOINT

A leitura real controlada anterior identificou `VT_000B` no caminho
`TEXT_RUN_CONTENT_INVALID / content_state=STRING /
DISALLOWED_C0_OR_C1_CONTROL`, sem mudança durante a auditoria. A reassessment
concreta concluiu que Google pode retornar esse valor em `TextRun.content` e
que a saída normalizada deve usar ASCII SPACE, sem remover o separador nem
introduzir uma quebra de linha.

O parser agora permite VT somente na validação da fonte `TextRun.content`, por
um parâmetro privado com padrão estrito; os demais callers de `_text()` continuam
rejeitando-o. Tipo, limite, UTF-8 estrito e os demais controles são validados
antes de comparar o span UTF-16 original. Após span correto, VT é substituído
um-por-um por SPACE e o tratamento existente de U+E907 continua em seguida.
Essa transformação conserva comprimento UTF-16 e UTF-8, provenance, limites
de chunk e continuação; VT-only segue o filtro whitespace existente. A
rejeição dos outros cinco grupos C0/C1, TAB/LF/CR, limite de 32 MiB, UTF-8,
U+E907 e taxonomia pública permanecem inalterados. O scaffold privado
`failing_branch`, `content_state`, `string_failure_reason` e `control_range`
foi mantido para a validação real pós-fix.

Os testes locais confirmam VT-only, texto misto, repetição e bordas, mismatch
de índice UTF-16, isolamento de metadata genérica, interação com U+E907,
preservação TAB/LF/CR, os controles vizinhos, provenance e chunking com
continuação comparados a uma entrada sintética equivalente com espaço. Foram
**194 testes focados** e **1051 testes na regressão completa**, sem falhas e
acima do baseline de 1040. O catálogo permaneceu em 24 tools (20 Read, 4
Content, 0 Write), sem duplicatas; `server.py` não mudou e `mcp.run()` continua
no final absoluto.

Não houve chamadas Google/Drive/Docs, Workspace MCP, rede ou autenticação; as
variáveis de configuração Google e o alvo diagnóstico não foram necessários.
Os 27 caminhos preexistentes foram preservados e somente
`google_docs.py`, `test_google_docs_content.py`, `docs/04_PHASE_STATUS.md` e
este histórico receberam delta. Staging, commit e push = zero; checkpoint não
autorizado. Próximo gate: `GOOGLE_DOCS_TEXT_RUN_VT_TARGETED_REAL_VALIDATION_V1`,
com novo snapshot e exatamente uma leitura real, sem retry. 1.5.4 permanece
incompleta.

## 21/09/2026 — WORKSPACE CONTENT 1.5.4 — VT REAL VALIDATION V1B + CONTROL RANGE CLEANUP V1 — COMPLETE / SEM CHECKPOINT

A validação real pós-fix V1B, executada manualmente pelo operador uma única
vez (`manual retries=0`), resolveu o mesmo alvo e invocou o content-reader de
produção exatamente uma vez. O precondition de ADC pós-reauth estava
**HEALTHY** e a resolução do alvo passou; o
resultado foi `PROCESSED`, com **2 chunks**, sem continuação e
`CHANGED_DURING_AUDIT=NO`. A falha anterior
`TEXT_RUN_CONTENT_INVALID / STRING / DISALLOWED_C0_OR_C1_CONTROL / VT_000B`
não se repetiu: o leitor avançou além do defeito, nenhuma falha mais profunda
foi observada e a validação real da correção VT foi **PASS**.

A limpeza removeu o campo privado `control_range`, o classificador das seis
faixas e a captura/assertions incident-only. `failing_branch`, `content_state`,
`string_failure_reason` e o coletor context-local, efêmero,
first-failure-only e disabled-by-default foram mantidos. A alteração não tocou
o caminho de parsing, a política C0/C1, a normalização VT→SPACE, a validação de
span UTF-16, provenance ou chunking. `FailureStage`, `StructuralFailureKind`
e `ParagraphFailureKind`, catálogo e schemas MCP também permaneceram
inalterados.

Foram **190 testes focados** e **1047 testes na regressão completa**, sem
falhas. Em relação aos baselines 194/1051, foram removidos 4 casos privados
redundantes/incident-only, nenhum foi adicionado e a variação líquida foi
**-4**; a cobertura de comportamento de controles vizinhos e a regressão de
VT permaneceram. O catálogo continua em 24 tools (20 Read, 4 Content, 0 Write),
sem duplicatas; `server.py` não foi alterado e `mcp.run()` segue como operação
final absoluta.

Não houve chamadas Google/API/auth nesta limpeza; a evidência V1B acima é o
resultado sanitizado fornecido pelo operador. As 27 alterações preexistentes
foram preservadas. Docs/04 e docs/05 foram sincronizados. A implementação
funcional da fase 1.5.4 está completa; revisão final e checkpoint/commit
permanecem pendentes. Staging, commit e push = zero; checkpoint não autorizado.

## 21/09/2026 — WORKSPACE CONTENT 1.5.4 — GOOGLE DOCS FINAL REVIEW V1 + CHECKPOINT V1 — COMPLETE

A Final Review V1 examinou o diff completo autorizado de Google Docs 1.5.4 e
verificou o fluxo de leitura, a normalização VT→SPACE após validação UTF-16,
o catálogo público, o `mcp.run()` como operação final, a remoção do diagnóstico
privado `control_range`, a cobertura de regressão e a higiene do repositório.
Foram encontrados **0 achados bloqueantes** e **0 não bloqueantes**; a prontidão
para checkpoint foi aprovada.

A validação real pós-fix V1B permanece **PASS**: uma resolução de alvo e uma
invocação do leitor de produção resultaram em `PROCESSED`, **2 chunks**, sem
continuação, sem TOCTOU e sem repetição do defeito VT; nenhuma falha mais
profunda foi observada. O conjunto final reteve **190 testes focados** e
**1047 testes na regressão completa**, com zero falhas. A diferença de quatro
casos em relação aos baselines anteriores corresponde exclusivamente à remoção
dos casos privados incident-only de `control_range`.

Este commit estabelece o checkpoint de Google Docs Content 1.5.4. A
implementação funcional, validação real, limpeza diagnóstica, documentação e
revisão final estão completas. O catálogo permanece com 24 tools (20 Read,
4 Content, 0 Write), sem duplicatas. Nenhuma próxima fase foi iniciada; ela
aguarda autorização explícita. Não houve chamadas Google/API/auth, push ou
alterações de configuração nesta entrega.
