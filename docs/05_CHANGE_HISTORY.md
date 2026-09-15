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
