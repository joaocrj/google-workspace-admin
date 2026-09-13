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
