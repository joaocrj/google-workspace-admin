# Andamento das fases

Última consolidação documental: **21/09/2026 — WORKSPACE CONTENT 1.5.4 GOOGLE DOCS CHECKPOINT V1 / FINAL REVIEW PASS / 190 TESTES FOCAIS E 1047 NA REGRESSÃO APROVADOS / CHECKPOINT ESTABELECIDO NESTE COMMIT**. Esta árvore é a fonte
persistente do roadmap/status e combina o estado do código em `master`, os
commits e o inventário de validações fornecido pelo usuário. Atualize-a no
mesmo change set de qualquer avanço. Evidência de produção deve registrar
somente status e contagens seguras.

## Convenção de estados e evidências

Os estados formais de entregas são `✅ CONCLUÍDO`, `← EM ANDAMENTO`,
`⬜ PENDENTE` e `⚠️ BLOQUEADO`. Resultados como HTTP 200, contagens, hashes de
commit, VALIDADO, VERIFICADA e ADICIONADO são evidências, não estados
concorrentes; preserve-os como detalhes da entrega.

## ROADMAP SYNCHRONIZATION RULE

Sempre que uma entrega alterar o estado de uma fase, feature ou subetapa, este
arquivo deve ser atualizado no mesmo conjunto de mudanças.

Isso inclui, quando aplicável: `PLAN → IMPLEMENT → REAL VALIDATION →
REVIEW/CHECKPOINT → COMMIT`.

Nenhuma feature será considerada documentalmente concluída enquanto sua
posição/status correspondente não estiver refletida nesta árvore.

**Ponteiro atual: FASE 1.5 — WORKSPACE CONTENT & DEEP ANALYSIS / 1.5.0–1.5.3 completos e checkpointed; Google Docs 1.5.4 está funcionalmente completo, validado no documento real e revisado: a correção VT→SPACE retornou `PROCESSED` com 2 chunks, sem continuação nem TOCTOU. A limpeza removeu o diagnóstico privado incident-specific `control_range`, mantendo `failing_branch`, `content_state` e `string_failure_reason`; Final Review V1 passou sem achados bloqueantes ou não bloqueantes. O checkpoint/commit desta entrega estabelece 1.5.4 como concluída. Nenhuma próxima fase foi iniciada; aguarda autorização explícita.** O CHECKPOINT V1 ficou
preservado como histórico bloqueado pelos achados FR-01 a FR-04, apesar de
**411 testes aprovados** naquele momento. O FINAL REVIEW V2 confirmou os quatro
achados corrigidos/verificados, **459 testes aprovados**, catálogo com 20 tools,
diff limpo e ausência de chamadas Google. O CHECKPOINT / COMMIT V1 é registrado
neste commit; nenhuma próxima fase foi iniciada.
Esse parágrafo preserva o histórico da consolidação anterior da camada Read;
o estado canônico corrente da Foundation Content está na árvore detalhada
abaixo, que preserva Reviews V1–V4 bloqueadas, Remediations V1–V4 e Review V5
aprovada.
Source Discovery DIAG V1,
Host Remediation FINAL PLAN V2, R2 Manual Lifecycle e a REAL GOOGLE CALL V9
histórica foram concluídos. O PLAN V1 e o IMPLEMENT V1 da Consolidação da
camada Read também foram concluídos localmente. A migração manual da DWD foi
confirmada pelo usuário. A remediação local de observabilidade foi concluída; Users foi
aprovado na REAL VALIDATION V4, Groups na REAL VALIDATION V1, Group Members nas
REAL VALIDATION V1 e V2 e OrgUnits na REAL VALIDATION V1, todos com chamadas
limitadas e sem exposição de registros. A validação DWD readonly está completa
e a remediação dos quatro achados do Final Review V1 foi concluída localmente.
A REAL VALIDATION V3 também ficou bloqueada em D9: o executor não
disponibilizou o contrato diagnóstico seguro, e o carregamento da remediação
pelo host permaneceu não confirmável. Não houve nova tentativa ou teste de
Groups. Depois disso, o usuário concluiu manualmente o restart completo do
Codex e a reautenticação da ADC. O host novo expôs catálogo compatível; a
remediação interna é inferida a partir do host novo, não diretamente provada
pelo schema.

```text
FASE 1 — READ / ADMIN INVENTORY
│
├── 1. Directory — identidade e estrutura                 ✅ CONCLUÍDO
│   ├── Users                                              ✅ CONCLUÍDO
│   │   ├── API Directory                                   ✅ CONCLUÍDO
│   │   ├── endpoint `/admin/directory/v1/users`            ✅ CONCLUÍDO
│   │   ├── scope histórico `admin.directory.user`; CODE TARGET `admin.directory.user.readonly` ✅
│   │   ├── módulo `directory/users.py`                     ✅ CONCLUÍDO
│   │   ├── workspace_users_list                            ✅ CONCLUÍDO
│   │   └── workspace_user_get                              ✅ CONCLUÍDO
│   ├── Groups                                             ✅ CONCLUÍDO
│   │   ├── endpoint `/admin/directory/v1/groups`           ✅ CONCLUÍDO
│   │   ├── scope histórico `admin.directory.group`; CODE TARGET `admin.directory.group.readonly` ✅
│   │   ├── módulo `directory/groups.py`                    ✅ CONCLUÍDO
│   │   └── workspace_groups_list                           ✅ CONCLUÍDO
│   ├── Group Members                                      ✅ CONCLUÍDO
│   │   ├── endpoint `/admin/directory/v1/groups/{groupKey}/members` ✅ CONCLUÍDO
│   │   ├── scope histórico `admin.directory.group.member`; CODE TARGET `admin.directory.group.member.readonly` ✅
│   │   ├── módulo `directory/group_members.py`             ✅ CONCLUÍDO
│   │   └── workspace_group_members_list                    ✅ CONCLUÍDO
│   ├── Organizational Units — Read                        ✅ CONCLUÍDO
│   │   ├── endpoint `/admin/directory/v1/customer/my_customer/orgunits` ✅ CONCLUÍDO
│   │   ├── scope histórico `admin.directory.orgunit`; CODE TARGET `admin.directory.orgunit.readonly` ✅
│   │   ├── módulo `directory/orgunits.py`                  ✅ CONCLUÍDO
│   │   └── workspace_orgunits_list                         ✅ CONCLUÍDO
│   ├── Mobile Devices                                     ✅ CONCLUÍDO — commit 6c3cc87
│   │   ├── API Directory e scope readonly                  ✅ CONCLUÍDO
│   │   ├── endpoint `/admin/directory/v1/customer/my_customer/devices/mobile` ✅
│   │   ├── módulo `directory/mobile_devices.py`            ✅ CONCLUÍDO
│   │   ├── workspace_mobile_devices_list                   ✅ CONCLUÍDO
│   │   ├── serializer allowlistado                         ✅ CONCLUÍDO
│   │   ├── testes unitários/protocolo MCP                  ✅ CONCLUÍDO
│   │   └── revisão + commit                                ✅ CONCLUÍDO — 6c3cc87
│   ├── ChromeOS Devices                                   ✅ CONCLUÍDO — commit 0610ebd
│   │   ├── API Directory                                   ✅ CONCLUÍDO — verificada
│   │   ├── endpoint `/admin/directory/v1/customer/my_customer/devices/chromeos` ✅
│   │   ├── scope `admin.directory.device.chromeos.readonly` ✅ CONCLUÍDO — adicionado
│   │   ├── módulo `directory/chromeos_devices.py`          ✅ CONCLUÍDO
│   │   ├── teste direto da API                             ✅ CONCLUÍDO — HTTP 200 / 0 dispositivos
│   │   ├── workspace_chromeos_devices_list                 ✅ CONCLUÍDO
│   │   ├── serializer e testes unitários/protocolo MCP     ✅ CONCLUÍDO
│   │   ├── execução real MCP/Codex                         ✅ CONCLUÍDO — 0 dispositivos
│   │   └── revisão + commit                                ✅ CONCLUÍDO — 0610ebd
│   ├── Roles & Admins                                     ✅ CONCLUÍDO — commit b589a91
│   │   ├── API/endpoints `roles.list` e `roleAssignments.list` ✅ CONCLUÍDO
│   │   ├── scope `admin.directory.rolemanagement.readonly` ✅ CONCLUÍDO — já presente
│   │   ├── módulos `directory/roles.py` e `directory/role_assignments.py` ✅
│   │   ├── teste direto                                   ✅ CONCLUÍDO — 15 roles / 3 assignments
│   │   ├── workspace_roles_list e workspace_role_assignments_list ✅ CONCLUÍDO
│   │   ├── serializers/testes e execução real MCP/Codex     ✅ CONCLUÍDO
│   │   └── revisão + commit                                ✅ CONCLUÍDO — b589a91
│   ├── Domains                                            ✅ CONCLUÍDO — commit 581b7d9
│   │   ├── endpoint `/admin/directory/v1/customer/my_customer/domains` ✅
│   │   ├── scope `admin.directory.domain.readonly`         ✅ CONCLUÍDO
│   │   ├── módulo `directory/domains.py` e serializer       ✅ CONCLUÍDO
│   │   ├── teste direto                                   ✅ CONCLUÍDO — HTTP 200 / 1 domínio
│   │   ├── workspace_domains_list e testes MCP             ✅ CONCLUÍDO
│   │   └── revisão + commit                                ✅ CONCLUÍDO — 581b7d9
│   └── Domain Aliases                                     ✅ CONCLUÍDO — commit c01fd11
│       ├── endpoint, scope e filtro `parentDomainName`      ✅ CONCLUÍDO
│       ├── módulo `directory/domain_aliases.py`             ✅ CONCLUÍDO
│       ├── workspace_domain_aliases_list e serializer       ✅ CONCLUÍDO
│       ├── correção de exposição indevida de serializer     ✅ CONCLUÍDO
│       ├── regressão `workspace_users_list` corrigida       ✅ CONCLUÍDO
│       ├── testes unitários/protocolo MCP                    ✅ CONCLUÍDO
│       ├── execução real MCP/Codex                         ✅ CONCLUÍDO — 1 alias
│       └── revisão + commit                                ✅ CONCLUÍDO — c01fd11
│
├── 2. Calendar — recursos corporativos                   ✅ CONCLUÍDO
│   ├── Buildings                                         ✅ CONCLUÍDO
│   │   ├── PLAN                                           ✅ CONCLUÍDO
│   │   ├── API Admin SDK Directory                         ✅ CONCLUÍDO
│   │   ├── endpoint `resources.buildings.list`             ✅ CONCLUÍDO
│   │   ├── scope `admin.directory.resource.calendar.readonly` ✅ CONCLUÍDO
│   │   ├── privilégio delegado `Calendar > View Resources` ✅ CONCLUÍDO
│   │   ├── módulo Directory/resources + tool MCP            ✅ CONCLUÍDO
│   │   ├── workspace_buildings_list                         ✅ CONCLUÍDO
│   │   ├── catálogo MCP                                    ✅ CONCLUÍDO — 13 tools
│   │   ├── descoberta MCP real: 13ª tool                    ✅ CONCLUÍDO — sem serializers expostos
│   │   ├── paginação por `nextPageToken` preservada         ✅ CONCLUÍDO — sem percurso automático
│   │   ├── cadeia keyless                                   ✅ CONCLUÍDO
│   │   ├── incidente ADC                                   ✅ DIAGNOSTICADO
│   │   ├── testes automatizados                             ✅ CONCLUÍDO — 76/76
│   │   ├── execução real MCP/Codex                          ✅ CONCLUÍDO — 0 Buildings / sem próxima página
│   │   └── revisão + commit                                 ✅ CONCLUÍDO — 9ce707f
│   ├── Resources / Salas                                  ✅ CONCLUÍDO
│   │   ├── PLAN/API/scope/privilégio                        ✅ CONCLUÍDO — reutilizados de Calendar resources
│   │   ├── scope `admin.directory.resource.calendar.readonly` ✅ CONCLUÍDO
│   │   ├── `resources.calendars.list`                       ✅ CONCLUÍDO
│   │   ├── módulo Directory/resources + tool MCP            ✅ CONCLUÍDO
│   │   ├── workspace_calendar_resources_list                ✅ CONCLUÍDO
│   │   ├── paginação por token, ordenação e filtro           ✅ CONCLUÍDO — sem percurso automático
│   │   ├── testes automatizados                              ✅ CONCLUÍDO — 100/100
│   │   ├── catálogo MCP                                     ✅ CONCLUÍDO — 14 tools
│   │   ├── execução real MCP/Codex                          ✅ CONCLUÍDO — 0 RECURSOS / sem próxima página
│   │   └── revisão + commit                                 ✅ CONCLUÍDO — 16565d6
│   └── Features                                           ✅ CONCLUÍDO
│       ├── PLAN                                           ✅ CONCLUÍDO — API, scope e privilégio
│       ├── scope `admin.directory.resource.calendar.readonly` ✅ CONCLUÍDO
│       ├── `resources.features.list`                       ✅ CONCLUÍDO
│       ├── módulo Directory/resources + tool MCP            ✅ CONCLUÍDO
│       ├── workspace_calendar_features_list                ✅ CONCLUÍDO
│       ├── testes automatizados                             ✅ CONCLUÍDO — 121/121
│       ├── catálogo MCP                                    ✅ CONCLUÍDO — 15 tools
│       ├── execução real MCP/Codex                          ✅ CONCLUÍDO — 0 FEATURES / sem próxima página
│       └── revisão + commit                                 ✅ CONCLUÍDO — 85bc49e
│
├── 3. Reports / Auditoria                                 ✅ CONCLUÍDO
│   ├── Admin Audit                                        ✅ CONCLUÍDO
│   │   ├── PLAN                                           ✅ CONCLUÍDO
│   │   ├── IMPLEMENT                                      ✅ CONCLUÍDO
│   │   ├── `workspace_admin_audit_list`                    ✅ CONCLUÍDO
│   │   ├── API/endpoint `/admin/reports/v1/activity/users/{userKey}/applications/admin` ✅
│   │   ├── scope `admin.reports.audit.readonly`             ✅ CONCLUÍDO — confirmado manualmente
│   │   ├── serializer allowlist e segurança                 ✅ CONCLUÍDO
│   │   ├── testes automatizados                              ✅ CONCLUÍDO — 155/155
│   │   ├── catálogo MCP                                     ✅ CONCLUÍDO — 16 tools
│   │   ├── REAL VALIDATION                                  ✅ CONCLUÍDO
│   │   │   ├── chamadas reais                               ✅ EXATAMENTE 1
│   │   │   ├── Activity                                      ✅ 1
│   │   │   └── next_page_token                               ✅ PRESENTE
│   │   └── commit                                            ✅ CONCLUÍDO — a3b10603692b835c2b11f3f1f8fbee6dc2473a05
│   ├── Login Audit                                        ✅ CONCLUÍDO
│   │   ├── PLAN                                             ✅ CONCLUÍDO
│   │   ├── IMPLEMENT                                          ✅ CONCLUÍDO — 17ª tool local
│   │   ├── `workspace_login_audit_list`                        ✅ CONCLUÍDO
│   │   ├── endpoint `/admin/reports/v1/activity/users/{userKey}/applications/login` ✅
│   │   ├── stale catalog / host                                ✅ REMEDIADO
│   │   ├── REDISCOVERY                                          ✅ CONCLUÍDO — catálogo real com 17 tools
│   │   ├── DIAGNOSTIC                                           ✅ CONCLUÍDO
│   │   ├── POST-RESTART CHECK                                   ✅ CONCLUÍDO
│   │   ├── scope necessário                                    ✅ CONCLUÍDO — já presente
│   │   ├── serializer allowlist específico                      ✅ CONCLUÍDO
│   │   ├── testes automatizados                                ✅ CONCLUÍDO — 191/191
│   │   ├── catálogo MCP                                       ✅ CONCLUÍDO — 17 tools
│   │   ├── REAL VALIDATION                                    ✅ CONCLUÍDO
│   │   │   ├── chamadas reais                                 ✅ EXATAMENTE 1
│   │   │   ├── Activity                                        ✅ 1
│   │   │   └── next_page_token                                 ✅ PRESENTE
│   │   └── commit                                              ✅ CONCLUÍDO — b572181e2ebdb4eda9fd81e049b5b4310c0674eb
│   ├── Drive Audit                                        ✅ CONCLUÍDO
│   │   ├── PLAN                                             ✅ CONCLUÍDO
│   │   ├── IMPLEMENT                                          ✅ CONCLUÍDO — 18ª tool local
│   │   ├── `workspace_drive_audit_list`                         ✅ CONCLUÍDO
│   │   ├── endpoint `/admin/reports/v1/activity/users/{userKey}/applications/drive` ✅
│   │   ├── stale host                                           ✅ REMEDIADO
│   │   ├── scope necessário                                     ✅ CONCLUÍDO — reutiliza admin.reports.audit.readonly
│   │   ├── serializer allowlist específico                       ✅ CONCLUÍDO
│   │   ├── testes automatizados                                 ✅ CONCLUÍDO — 230/230
│   │   ├── catálogo MCP                                        ✅ CONCLUÍDO — 18 tools
│   │   ├── REAL VALIDATION                                    ✅ CONCLUÍDO
│   │   │   ├── chamadas reais                                 ✅ EXATAMENTE 1
│   │   │   ├── Activity                                        ✅ 1
│   │   │   └── next_page_token                                 ✅ PRESENTE
│   │   └── commit                                              ✅ CONCLUÍDO — d48bfd386d162201036709f1303c767dcbc395a7
│   ├── User Usage                                         ✅ CONCLUÍDO
│   │   ├── PLAN                                             ✅ CONCLUÍDO — contrato aprovado
│   │   ├── IMPLEMENT                                          ✅ CONCLUÍDO — 19ª tool local
│   │   ├── `UserUsageReport.get`                              ✅ CONCLUÍDO
│   │   ├── `workspace_user_usage_get`                          ✅ CONCLUÍDO
│   │   ├── endpoint `/admin/reports/v1/usage/users/{userKey}/dates/{date}` ✅
│   │   ├── scope `admin.reports.usage.readonly`                ✅ CONCLUÍDO — sem alteração administrativa
│   │   ├── serializer allowlist e PII                            ✅ CONCLUÍDO — profile_id; e-mail/entityId omitidos
│   │   ├── testes automatizados                                 ✅ CONCLUÍDO — 264/264
│   │   ├── catálogo MCP                                        ✅ CONCLUÍDO — 19 tools
│   │   ├── primeira validação real                              ⚠️ ADC RefreshError
│   │   ├── gcloud ADC reauth                                    ✅ MANUAL
│   │   ├── REAL VALIDATION                                    ✅ CONCLUÍDO
│   │   │   ├── chamadas reais                                 ✅ EXATAMENTE 1
│   │   │   ├── requested report date                            ✅ 2026-09-10
│   │   │   ├── usageReports                                     ✅ 1
│   │   │   ├── next_page_token                                 ✅ PRESENTE
│   │   │   ├── warnings_present                                ✅ TRUE
│   │   │   └── warnings_count                                  ✅ 1
│   │   ├── cleanup diagnóstico                                  ✅ CONCLUÍDO — instrumentação temporária removida
│   │   ├── cleanup MCP temporário                               ✅ CONCLUÍDO — entrada temporária removida
│   │   ├── revisão documental                                  ✅ CONCLUÍDO
│   │   └── commit                                              ✅ CONCLUÍDO — 1792a65ee785c7f464e715c55a7f796d5c57c335
│   └── Customer Usage                                     ✅ CONCLUÍDO
│       ├── PLAN V1                                           ♻️ SUPERADO
│       ├── PLAN V2                                           ✅ CONCLUÍDO
│       │   ├── documentação oficial                            ✅ VERIFICADA
│       │   ├── `CustomerUsageReports.get`                       ✅
│       │   ├── `/admin/reports/v1/usage/dates/{date}`           ✅
│       │   ├── `admin.reports.usage.readonly`                    ✅
│       │   ├── `workspace_customer_usage_get`                    ✅ CONTRATO
│       │   ├── `date`                                            ✅ OBRIGATÓRIO
│       │   ├── `parameters`                                      ✅ OBRIGATÓRIO
│       │   ├── `page_token`                                      ✅ OPCIONAL
│       │   ├── allowlist                                         ✅ 10 accounts metrics
│       │   ├── métricas sensíveis                                ✅ EXCLUÍDAS
│       │   ├── métricas deprecated                               ✅ EXCLUÍDAS
│       │   ├── paginação automática                              ✅ NÃO
│       │   ├── retry                                              ✅ 0
│       │   ├── timeout                                            ✅ 30s
│       │   └── serializer                                         ✅ ALLOWLIST-FIRST
│       ├── IMPLEMENT V1                                      ✅ CONCLUÍDO
│       │   ├── arquivos autorizados                            ✅ EXATAMENTE 10
│       │   ├── `customer_usage.py`                              ✅
│       │   ├── `server.py`                                       ✅
│       │   ├── `test_customer_usage.py`                         ✅
│       │   ├── `test_mcp_protocol.py`                            ✅
│       │   ├── `test_server.py`                                  ✅
│       │   ├── documentação                                      ✅
│       │   ├── `workspace_customer_usage_get`                     ✅ IMPLEMENTADA
│       │   ├── helpers                                           ✅ NÃO EXPOSTOS
│       │   ├── `mcp.run()`                                       ✅ FINAL ABSOLUTO
│       │   ├── catálogo local                                    ✅ 20 tools
│       │   ├── testes automatizados                              ✅ 307/307
│       │   ├── `git diff --check`                                ✅
│       │   └── commit                                             ✅ CONCLUÍDO — feat: add workspace customer usage reports
│       ├── REAL VALIDATION V1                                  ⚠️ HOST 19 (histórico)
│       │   ├── host catalog                                    ⚠️ 19
│       │   ├── `workspace_customer_usage_get`                    ❌ AUSENTE
│       │   └── Google call                                      ⏭️ NÃO EXECUTADA
│       ├── REAL VALIDATION V2                                  ✅ DIAGNÓSTICO
│       │   └── restart externo                                  ⚠️ NECESSÁRIO
│       ├── REAL VALIDATION V3                                  ⚠️ HOST 19 PÓS-RESTART (histórico)
│       ├── REAL VALIDATION V4                                  ✅ DIAGNÓSTICO
│       │   ├── source                                            ✅ CORRETO
│       │   ├── decorator                                         ✅ CORRETO
│       │   ├── Python/package resolution                           ✅ CORRETO
│       │   ├── catálogo local                                    ✅ 20
│       │   └── host                                              ⚠️ 19
│       ├── REAL VALIDATION V5                                  ✅ DIAGNÓSTICO
│       │   ├── direct stdio initialize                           ✅
│       │   ├── `tools/list`                                       ✅
│       │   ├── direct stdio                                      ✅ 20
│       │   ├── `workspace_customer_usage_get`                     ✅ PRESENTE
│       │   ├── `workspace_user_usage_get`                         ✅ PRESENTE
│       │   ├── helpers                                           ✅ AUSENTES
│       │   └── host                                              ⚠️ 19
│       ├── REAL VALIDATION V6                                  ✅ DIAGNÓSTICO
│       │   ├── Codex CLI                                         ✅ 0.154.0-alpha.6.2
│       │   ├── `config.toml`                                     ✅ EXISTE
│       │   ├── `google_workspace_admin`                           ✅ PRESENTE
│       │   ├── CLI registry                                      ⚠️ 0 MCPs
│       │   └── host                                              ⚠️ 19
│       ├── REAL VALIDATION V7                                  ✅ DIAGNÓSTICO
│       │   ├── TOML                                              ✅ VÁLIDO
│       │   ├── `mcp_servers`                                     ✅ VÁLIDO
│       │   ├── profiles                                           ✅ NENHUM
│       │   └── causa                                              ⚠️ NÃO OBSERVÁVEL
│       ├── REAL VALIDATION V8                                  ✅ CONCLUÍDO
│       │   ├── `--config`                                         ✅ INVESTIGADO
│       │   ├── semântica                                          ✅ key=value override
│       │   ├── config file path                                   ❌ NÃO SUPORTADO
│       │   ├── explicit file test                                 ⏭️ NÃO EXECUTADO
│       │   └── classificação                                      ✅ Z3
│       ├── HOST REMEDIATION                                    ✅ CONCLUÍDO — R2 SUCCESS
│       │   │
│       │   ├── PLAN V1                                           ✅ CONCLUÍDO
│       │   │   ├── reload/refresh                                  ❌ NÃO DISPONÍVEL
│       │   │   ├── `codex mcp add`                                ✅ DISPONÍVEL
│       │   │   ├── aplicabilidade ao host                         ⚠️ NÃO COMPROVADA
│       │   │   ├── re-registration                                 ⏭️ NÃO EXECUTADO
│       │   │   └── estratégia                                      ✅ DESCOBRIR FONTE DO HOST
│       │   ├── SOURCE DISCOVERY DIAG V1                          ✅ CONCLUÍDO — H6 — HOST SOURCE STILL NOT OBSERVABLE
│       │   │   ├── identificar processo host                       ✅ OBSERVADO — detalhes limitados
│       │   │   ├── identificar processo MCP original               ⚠️ NÃO OBSERVÁVEL
│       │   │   ├── PID / parent PID                               ⚠️ NÃO ACESSÍVEIS
│       │   │   ├── process start time                             ⚠️ NÃO DETERMINÁVEL
│       │   │   ├── comparar timestamps                            ⚠️ NÃO DETERMINÁVEL
│       │   │   ├── localizar state/config do host                 ⚠️ NÃO LOCALIZADO
│       │   │   └── determinar fonte MCP                            ⚠️ NÃO OBSERVÁVEL
│       │   ├── ROADMAP PERSISTENT SYNC                            ✅ CONCLUÍDO — regra aplicada
│       │   ├── FINAL PLAN V2                                     ✅ CONCLUÍDO
│       │   │   ├── R1 — MCP-only reinstantiation                   ❌ NÃO DISPONÍVEL
│       │   │   ├── R2 — completely fresh Codex host                 ✅ SELECIONADA — MANUAL LIFECYCLE
│       │   │   ├── R3 — CLI re-registration                         ⚠️ NÃO RECOMENDADA
│       │   │   ├── R4 — manual host state/config                    ❌ NÃO DISPONÍVEL
│       │   │   └── automated remediation                            ✅ NO SAFE AUTOMATED REMEDIATION
│       │   ├── R2 — Manual Lifecycle                              ✅ CONCLUÍDO — SUCCESS
│       │   │   ├── encerramento automático                         ✅ NÃO EXECUTADO
│       │   │   ├── handoff manual ao usuário                       ✅ PREPARADO
│       │   │   └── processos Python genéricos                      ✅ NÃO ENCERRAR
│       │   ├── REMEDIATION                                         ✅ CONCLUÍDO — ação manual
│       │   │   └── resultado                                        ✅ R2 SUCCESS
│       │   └── HOST VALIDATION V1                                ✅ PASSED
│       │       ├── original host catalog                            ✅ 20
│       │       ├── `workspace_customer_usage_get`                    ✅ PRESENTE
│       │       ├── `workspace_user_usage_get`                         ✅ PRESENTE
│       │       └── helpers                                         ✅ AUSENTES
│       ├── REAL GOOGLE CALL                                      ✅ CONCLUÍDO — V9 PASSED
│       │   ├── REAL VALIDATION V9                                ✅ PASSED
│       │   ├── requested report date                              ✅ 2026-09-10
│       │   ├── execution date                                     ✅ 2026-09-12
│       │   ├── calls                                               ✅ EXACTLY 1
│       │   ├── retry                                               ✅ 0
│       │   ├── pagination                                          ✅ 0
│       │   ├── usageReports                                        ✅ 1
│       │   ├── next_page_token                                     ✅ ABSENT
│       │   ├── warnings_present                                    ✅ TRUE
│       │   └── warnings_count                                      ✅ 1
│       ├── FINAL REVIEW V1                                       ✅ PASSED
│       └── CHECKPOINT / COMMIT                                   ✅ CONCLUÍDO — THIS COMMIT
│           └── `feat: add workspace customer usage reports`       ✅ CONCLUÍDO
│
└── 4. Consolidação da camada Read                         ✅ CONCLUÍDO — CHECKPOINT / COMMIT V1
    ├── PLAN V1                                             ✅ CONCLUÍDO
    ├── paginação explícita com nextPageToken               ✅ CONCLUÍDO — sem auto-pagination
    ├── tratamento uniforme de erros                       ✅ CONCLUÍDO — erros HTTP seguros
    ├── revisão de scopes mínimos                          ✅ CONCLUÍDO — CODE TARGET readonly
    │   └── DWD READONLY MIGRATION                         ✅ CONCLUÍDO — confirmação manual do usuário
    ├── serialização consistente                           ✅ CONCLUÍDO — aliases allowlistados
    ├── consistência do catálogo MCP                       ✅ CONCLUÍDO — 20 tools únicas
    ├── documentação final                                 ✅ CONCLUÍDO — docs 01–05
    ├── inventário/testes finais                           ✅ CONCLUÍDO — suíte local aprovada
    ├── IMPLEMENT V1                                       ✅ CONCLUÍDO
    ├── REMEDIATION PLAN V1                                ✅ CONCLUÍDO
    ├── REMEDIATION IMPLEMENT V1                           ✅ CONCLUÍDO — FR-01 a FR-04 corrigidos
    │   ├── FR-01 / StrictInt na fronteira MCP              ✅ CORRIGIDO — 14 max_results
    │   ├── FR-02 / contexto canônico de operação           ✅ CORRIGIDO — quatro operações
    │   ├── FR-03 / fixtures sintéticas                     ✅ CORRIGIDO — identificador real removido
    │   ├── FR-04 / documentação sincronizada               ✅ CORRIGIDO — docs/01–05
    │   └── testes locais                                   ✅ 459 passed; 48 casos adicionados
    ├── FINAL REVIEW V1                                    ⚠️ BLOQUEADO — FR-01 a FR-04
    │   ├── baseline                                       ✅ master; HEAD 6624305e8a60de09efda5b6626b317755c07536c
    │   ├── arquivos / staging                             ✅ 25 autorizados; 0 inesperados; staging vazio
    │   ├── testes locais                                  ✅ 411 passed; uv run pytest -q
    │   ├── catálogo / invariantes                         ✅ 20 tools; helpers ausentes; mcp.run final
    │   ├── quatro validações readonly                     ✅ PASSED — histórico preservado abaixo
    │   ├── FR-01 / validação inteira na fronteira MCP      ⚠️ BLOQUEADO — coerção antes do wrapper
    │   ├── FR-02 / contexto seguro de operação             ⚠️ BLOQUEADO — quatro nomes viram unknown
    │   ├── FR-03 / identificador real em fixtures          ⚠️ BLOQUEADO — ocorrência preexistente no HEAD
    │   └── FR-04 / consistência documental                ⚠️ BLOQUEADO — estados e cobertura divergentes
    ├── CHECKPOINT / COMMIT                                ✅ CONCLUÍDO — este commit
    ├── VALIDATION                                         ✅ CONCLUÍDO — quatro scopes readonly PASSED
        ├── DWD VALIDATION / user.readonly                 ✅ CONCLUÍDO — Real Validation V4 PASSED
        │   ├── VALIDATION V1                              ⚠️ BLOQUEADO — D9
        │   ├── DIAGNOSTIC V1                              ✅ CONCLUÍDO — source/host MATCH
        │   ├── EVIDENCE V1                                ⚠️ BLOQUEADO — D9; decisão R7
        │   ├── VALIDATION V2                              ⚠️ BLOQUEADO — D9
        │   │   └── DIAGNOSTIC VALIDATION V2               ⚠️ CONCLUÍDO — evidência insuficiente preservada
        │   ├── REMEDIATION PLAN V1                        ✅ CONCLUÍDO
        │   ├── REMEDIATION IMPLEMENT V1                   ✅ CONCLUÍDO — sem chamada Google
        │   ├── REAL VALIDATION V3                         ⚠️ BLOQUEADO — D9; host/remediação não confirmável
        │   ├── HOST REMEDIATION V1                        ✅ CONCLUÍDO — restart completo manual do Codex
        │   │   ├── launcher                                      ✅ EXPECTED
        │   │   └── processo genérico encerrado                    ✅ NÃO EXECUTADO
        │   ├── POST-RESTART HOST VALIDATION V1             ✅ CONCLUÍDO — source/host MATCH
        │   │   ├── catálogo do host                              ✅ 20 tools
        │   │   ├── workspace_users_list                           ✅ PRESENTE
        │   │   ├── max_results / page_token                        ✅ PRESENTES
        │   │   ├── fresh host após restart completo                ✅ SIM
        │   │   └── internal remediation                            ✅ INFERIDA DO HOST NOVO
        │   └── REAL VALIDATION V4                         ✅ CONCLUÍDO — user.readonly PASSED
        │       ├── chamada Users                                  ✅ 1 chamada, max_results=1
        │       ├── users_count / next_page_token                   ✅ 1 / PRESENTE; token não utilizado
        │       ├── scope                                            ✅ admin.directory.user.readonly
        │       └── retry/paginação adicional                         ✅ NÃO EXECUTADOS
        ├── DWD VALIDATION / group.readonly                ✅ CONCLUÍDO — Real Validation V1 PASSED
        │   └── GROUP READONLY REAL VALIDATION V1          ✅ CONCLUÍDO
        │       ├── chamada Groups                                  ✅ 1 chamada, max_results=1
        │       ├── groups_count / next_page_token                   ✅ 1 / AUSENTE
        │       ├── scope                                            ✅ admin.directory.group.readonly
        │       └── retry/paginação adicional                         ✅ NÃO EXECUTADOS
        ├── DWD VALIDATION / group.member.readonly         ✅ CONCLUÍDO — Real Validation V2 PASSED
        │   ├── GROUP MEMBER READONLY REAL VALIDATION V1  ✅ CONCLUÍDO — PASSED
        │   │   ├── chamada Group Members                         ✅ 1 chamada, max_results=1
        │   │   ├── members_count / next_page_token                 ✅ 0 / AUSENTE
        │   │   ├── scope                                           ✅ admin.directory.group.member.readonly
        │   │   └── retry/paginação adicional                        ✅ NÃO EXECUTADOS
        │   ├── MANUAL GROUP KEY INPUT                    ✅ PROVIDED
        │   └── GROUP MEMBER READONLY REAL VALIDATION V2  ✅ CONCLUÍDO — PASSED
        │       ├── chamada Group Members                         ✅ 1 chamada, max_results=1
        │       ├── members_count / next_page_token                 ✅ 0 / AUSENTE
        │       ├── scope                                           ✅ admin.directory.group.member.readonly
        │       └── retry/paginação adicional                        ✅ NÃO EXECUTADOS
        └── DWD VALIDATION / orgunit.readonly              ✅ CONCLUÍDO — Real Validation V1 PASSED
            └── ORGUNIT READONLY REAL VALIDATION V1       ✅ CONCLUÍDO
                ├── chamada OrgUnits                            ✅ 1 chamada, path=/, type=children
                ├── orgunits_count / next_page_token              ✅ 2 / NÃO SUPORTADO
                ├── scope                                        ✅ admin.directory.orgunit.readonly
                └── retry/paginação adicional                     ✅ NÃO EXECUTADOS
    └── FINAL REVIEW V2                                    ✅ CONCLUÍDO — FR-01 a FR-04 FIXED / VERIFIED
        ├── revisão integral do diff                         ✅ 25 caminhos; 0 inesperados; 0 não autorizados
        ├── FR-01 / StrictInt na fronteira MCP                ✅ VERIFIED — 14/14; rejeição antes da execução
        ├── FR-02 / contexto canônico de operação              ✅ VERIFIED — 4/4; nenhum `unknown`
        ├── FR-03 / fixtures sintéticas                        ✅ VERIFIED — identificador real ausente
        ├── FR-04 / documentação                               ✅ VERIFIED — docs/01–05 sincronizados
        ├── testes direcionados / suíte completa                ✅ 272 / 459 passed; sem skips/xfails novos
        ├── catálogo / invariantes                              ✅ 20 tools únicas; helpers ausentes; mcp.run final
        ├── semântica Google                                    ✅ request, scopes, sucesso e paginação inalterados
        └── próximo ponteiro                                    → STOP — próxima fase não iniciada

FASE 2 — WRITE / ADMINISTRATION                            ⬜ PENDENTE — POSTERIOR
│
├── Organizational Units — Write                           ⬜ FUTURO
│   ├── workspace_orgunit_create                           ⬜ PENDENTE
│   ├── workspace_orgunit_update                           ⬜ PENDENTE
│   ├── workspace_orgunit_move                             ⬜ PENDENTE
│   └── workspace_orgunit_delete                           ⬜ PENDENTE
│
├── Group Management                                       ⬜ FUTURO
│   ├── criar grupos                                       ⬜ PENDENTE
│   ├── atualizar grupos                                   ⬜ PENDENTE
│   ├── adicionar/remover membros                          ⬜ PENDENTE
│   └── alterar MEMBER / MANAGER / OWNER                   ⬜ PENDENTE
│
└── User Lifecycle                                         ⬜ FUTURO
    ├── criar usuário                                      ⬜ PENDENTE
    ├── suspender/reativar                                 ⬜ PENDENTE
    ├── alterar OU                                         ⬜ PENDENTE
    ├── resetar senha                                      ⬜ PENDENTE
    └── administração/delegação                            ⬜ PENDENTE
```

## Evidência de qualidade preservada

- Em 11/09/2026, a implementação local de Buildings confirmou **76/76 testes
  aprovados** em `uv run pytest -v`, incluindo testes unitários, serialização e
  protocolo MCP com mocks. Após reautenticação manual da ADC pelo usuário, a
  suíte foi confirmada novamente com **76/76 testes aprovados** e
  `git diff --check` foi aprovado. Com DWD e privilégio delegado confirmados
  administrativamente, a cadeia keyless ADC → IAM `signJwt` → DWD → OAuth →
  Directory foi validada. Um MCP `stdio` novo descobriu 13 tools e a tool
  Buildings; a única chamada real limitada foi bem-sucedida com zero Buildings
  e sem próxima página. Nenhum nome, endereço, coordenada ou token de
  paginação foi registrado.
- Em 11/09/2026, Resources / Salas recebeu implementação local da coleção
  `resources.calendars`, serialização limitada, paginação por token e testes
  unitários/protocolo MCP com mocks; a suíte completa confirmou **100/100
  testes aprovados**. Um processo MCP `stdio` novo redescobriu 14 tools sem
  helpers/serializers expostos e validou a cadeia keyless com a única chamada
  real limitada a `max_results=1`: zero Resources / Salas e sem próxima página.
  Nenhum dado de recurso, token ou credencial foi registrado. O checkpoint Git
  desta entrega é registrado nesta mudança.
- Em 11/09/2026, Features recebeu PLAN aprovado e implementação local da
  coleção `resources.features`, serialização limitada a `feature_name`,
  paginação por token e a 15ª tool MCP. A suíte local confirmou **121/121
  testes aprovados**; os testes unitários e de protocolo usam mocks. Após a
  confirmação segura da ADC, um processo MCP `stdio` novo redescobriu 15 tools
  sem helpers/serializers expostos e validou a cadeia keyless com uma única
  chamada real limitada a `max_results=1`: zero Features e sem próxima página.
  Nenhum dado de Feature, token ou credencial foi registrado; o checkpoint Git
  desta entrega conclui Features e o bloco Calendar — recursos corporativos.
- Em 11/09/2026, Admin Audit recebeu PLAN aprovado e implementação local da
  Reports API `activities.list` para `applicationName=admin`, serialização
  limitada de eventos e parâmetros não sensíveis, a 16ª tool MCP e 155/155
  testes locais aprovados. A DWD para `admin.reports.audit.readonly` e o
  sujeito delegado Superadministrador foram confirmados manualmente pelo
  usuário. A REAL VALIDATION foi executada exatamente uma vez pelo launcher
  Python da `.venv`, com sucesso, 1 Activity e próxima página presente. Nenhum
  dado de auditoria, credencial, token ou payload real foi registrado; o
  checkpoint Git foi concluído no commit `a3b1060`.
- Em 11/09/2026, a REAL VALIDATION do Drive Audit foi concluída exclusivamente
  pelo MCP original carregado pelo host, com exatamente uma chamada limitada a
  `max_results=1`: sucesso, 1 Activity e `next_page_token` presente. A cadeia
  keyless até `activities.list` com `applicationName=drive` foi validada; não
  houve retry ou paginação adicional, e nenhum conteúdo real de Activity,
  token, credencial ou payload foi persistido. O checkpoint Git foi concluído
  no commit `d48bfd3`.
- As tentativas anteriores de validação em `codexsandboxoffline` foram
  diagnosticadas como restrições locais: socket para `oauth2.googleapis.com`,
  `UnsupportedOperation` causado por `stderr=io.StringIO` e cache do `uv` sem
  permissão. A redescoberta pelo launcher Python da `.venv` inicializou o MCP
  com 16 tools sem alteração de código ou configuração administrativa.
- Em 11/09/2026, o restart manual do Codex foi seguido pelo POST-RESTART CHECK:
  o host carregou o launcher Python da `.venv`, redescobriu o catálogo real com
  17 tools e confirmou `workspace_login_audit_list` sem helpers/serializers
  expostos. A REAL VALIDATION — tentativa 3 — executou exatamente uma chamada
  MCP, com sucesso, 1 Activity e próxima página presente. Nenhum conteúdo de
  Activity, PII, credencial ou token foi registrado; o checkpoint Git foi
  concluído nesta entrega.
- Na consolidação documental de 10/09/2026, `uv run pytest -v` confirmou
  **56/56 testes aprovados**. `git diff --check` também foi aprovado.
- Em `c01fd11`, o inventário fornecido já registrava **56/56 testes**,
  `git diff --check` e árvore de trabalho limpa.
- A revisão do catálogo concluiu com 12 ferramentas, incluindo aliases e a
  regressão de `workspace_users_list` corrigida.
- A contagem textual de 14 para um retorno de 15 roles foi identificada como
  interpretação do modelo, não erro do MCP.
- Em 11/09/2026, uma reconstrução independente de contexto pelo Codex confirmou
  a coerência da arquitetura keyless, das 12 tools, dos invariantes de
  `server.py`, do checkpoint `c01fd11` e da FASE 1. Essa auditoria não executou
  novamente a suíte; a última evidência executada permanece 56/56 em
  10/09/2026.
- Em 12/09/2026, User Usage foi implementado localmente como a 19ª tool com
  `UserUsageReport.get`, scope `admin.reports.usage.readonly`, uma página por
  chamada, timeout de 30 segundos e nenhum retry. O serializer allowlistado
  preserva somente `date`, `profile_id` de `entity.profileId` e métricas seguras;
  `timestamp_last_login` é o nome atual e timestamps só aparecem quando
  explicitamente solicitados. `userEmail`, `entityId`, `customerId`,
  parâmetros desconhecidos, `stringValue`, `msgValue`, warnings brutos e o
  payload bruto ficam omitidos. A validação final, executada em `2026-09-12`
  para a data do relatório solicitado `date=2026-09-10`,
  confirmou catálogo com 19 tools, **264 passed**, `usageReports=1`,
  `next_page_token` presente, `warnings_present=true` e `warnings_count=1`,
  sem retry ou paginação adicional. Uma falha inicial opaca identificou
  `RefreshError` na autenticação local; o usuário reautenticou manualmente a
  ADC e a chamada seguinte foi bem-sucedida. Código funcional, DWD, scopes e
  Admin Console não foram alterados. A instrumentação diagnóstica temporária e
  o MCP temporário foram removidos; o checkpoint/commit foi concluído no
  commit `1792a65`.
- Em 12/09/2026, Customer Usage foi implementado localmente como a 20ª tool
  com `CustomerUsageReports.get` no endpoint `/usage/dates/{date}`. O contrato
  exige `date` e `parameters`, aceita `page_token` explícito, não envia
  `customerId`/`maxResults`, processa uma página, não faz retry e usa timeout de
  30 segundos. A allowlist inicial contém dez métricas integer de Accounts;
  métricas de outras aplicações, deprecated, strings, datas, mensagens,
  booleans e estruturas de identidade são omitidas. Testes locais concluíram
  com sucesso — **307 passed**. Os prechecks/diagnósticos V1–V7 registraram
  host com 19 tools, restart externo, processo stdio com 20 tools e arquivo
  TOML válido, sem causa adicional observável. V8 foi concluído com a
  investigação de `--config`, classificação Z3 e confirmação de que o caminho
  de arquivo não é suportado. O PLAN V1 de Host Remediation e o Source
  Discovery DIAG V1 foram concluídos; este último recebeu classificação H6 —
  host source still not observable. O FINAL PLAN V2 selecionou R2 — Manual
  Lifecycle; nenhum encerramento automático foi executado e o handoff manual
  aguarda o usuário. Naquele ponto, a REAL GOOGLE CALL permanecia bloqueada e
  não havia sido executada.

- Em 12/09/2026, a REAL VALIDATION V9 de Customer Usage foi concluída pelo MCP
  original do host com exatamente uma chamada autorizada: status de sucesso,
  `usageReports=1`, `next_page_token` ausente, warnings presentes (1), sem
  retry, sem paginação adicional e sem registrar valor de métrica, PII,
  credencial, token ou payload bruto.
- Em 12/09/2026, a FINAL REVIEW de Customer Usage foi concluída com **307
  passed**, os 11 arquivos classificados como EXPECTED, implementação,
  registro MCP, serializer, invariantes de `server.py`, documentação e busca
  de segurança aprovados. O roadmap foi sincronizado; CHECKPOINT / COMMIT foi
  concluído neste commit. Nenhum push foi realizado.
- Em 12/09/2026, a Consolidação da camada Read — PLAN V1 e IMPLEMENT V1 — foi
  concluída localmente. Os sete módulos Directory pagináveis passaram a usar
  `max_results`/`page_token` explícitos, sem auto-pagination; os quatro CODE
  TARGETS de scope `.readonly` foram aplicados sem alterar DWD; falhas HTTP,
  shapes e aliases aninhados receberam tratamento seguro. O catálogo permaneceu
  com 20 tools únicas, helpers não expostos e `mcp.run()` final absoluto. A
  suíte local concluiu com **398 passed** (`307` anteriores + `91` testes), e
  `git diff --check` foi aprovado. Nenhuma chamada Google, Workspace ou MCP
  funcional foi realizada nesta entrega. A migração DWD readonly continuava
  manual e pendente naquele checkpoint; a validação posterior permanece
  registrada separadamente abaixo.

- Em 13/09/2026, após confirmação manual do usuário para os quatro scopes
  Directory `.readonly`, a validação DWD READONLY de Users executou exatamente
  uma chamada limitada de `workspace_users_list(max_results=1,
  page_token=None)`. O host expôs 20 tools e a tool estava presente, mas o
  retorno não forneceu uma categoria segura identificável; o resultado foi
  registrado como `OTHER SAFE CATEGORY`. Não houve retry, segunda página ou
  registro de dados de usuário. Groups, Group Members e OrgUnits permanecem
  pendentes.

- Em 13/09/2026, a DWD USERS DIAGNOSTIC VALIDATION V2 executou exatamente uma
  segunda e última chamada controlada de `workspace_users_list(max_results=1,
  page_token=None)`. O executor retornou bloqueio, mas não disponibilizou tipo
  de exceção, mensagem segura, status HTTP, operação, categoria ou camada. A
  mensagem foi retida; a classificação permanece D9 — evidência insuficiente.
  Não houve retry, paginação, exposição de dados ou alteração de ADC/DWD. O
  próximo ponteiro é REMEDIATION.

### READ-LAYER-CONSOLIDATION-FINAL-REVIEW-V1 — 13/09/2026

Resultado: **BLOCKED**. Próxima entrega: **READ CONSOLIDATION REMEDIATION**,
dependente de autorização separada. Nenhum source ou teste foi corrigido.
Esta atualização de docs/04 e docs/05 registra somente o resultado do review;
as inconsistências documentais encontradas permanecem explicitamente pendentes.

- **FR-01 — P1:** as sete tools Directory usam anotações `int` comuns. O
  validador de argumentos do SDK MCP converte `True`, `1.0` e a string numérica
  `"1"` para inteiro antes de `validate_max_results`; os 21 casos foram
  aceitos numa verificação local do modelo de argumentos, sem invocar tools.
  A rejeição estrita nos módulos não garante a rejeição na fronteira pública.
  Remediação proposta: impedir coerção nessa fronteira e acrescentar testes
  de argumentos/protocolo com dependências mockadas. Arquivos candidatos:
  `src/google_workspace_admin/server.py` e `tests/test_mcp_protocol.py`.
- **FR-02 — P2:** `Directory members.list`, `Directory mobiledevices.list`,
  `Directory chromeosdevices.list` e `Directory roleAssignments.list` não
  correspondem aos aliases de `http_errors.py`. A construção local de erros
  confirma `operation=unknown`, embora code e HTTP status sejam preservados.
  Remediação proposta: alinhar os aliases aos chamadores e testar o contexto
  das quatro operações; nenhum payload deve ser incorporado ao diagnóstico.
  Arquivos candidatos: `src/google_workspace_admin/http_errors.py` e testes
  dos quatro módulos correspondentes.
- **FR-03 — P2:** o identificador fornecido manualmente coincide com quatro
  literais já presentes nos testes (dois em `tests/test_server.py` e dois em
  `tests/test_mcp_protocol.py`). A mesma contagem existe no HEAD baseline;
  portanto não se trata de persistência nova pela validação. Não há ocorrência
  nos documentos. Mesmo assim, o critério absoluto de ausência em arquivos
  não é satisfeito. Remediação proposta: substituir essas fixtures por dados
  sintéticos nos dois arquivos, preservando o comportamento dos testes.
  O valor não é reproduzido neste registro.
- **FR-04 — P2:** docs/01 ainda lista scopes broad sob o título de scopes do
  código e marca a migração como PENDING; docs/02 e docs/03 também a tratam
  como pendente. Em docs/04, o agregador VALIDATION ainda aguarda Groups,
  apesar dos quatro filhos PASSED, e a reautenticação manual ADC está na
  narrativa, sem nó próprio na árvore Users. O runbook generaliza o contrato
  estruturado para todas as tools READ, mas a normalização local/fallback
  existe especificamente em Users; outros módulos ainda usam caminhos
  anteriores. As novas linhas de docs/05 estão separadas da tabela por linhas
  vazias, e há referência de User Usage como superada por V9 de Customer Usage.
  Remediação proposta: sincronizar docs/01–05 com a cobertura efetiva e manter
  todos os eventos históricos, sem novas validações reais por ritual.

Verificações aprovadas: quatro scopes `.readonly` exclusivos no source;
paginação explícita dos sete módulos; aliases aninhados allowlistados;
catálogo source/documentação/host com 20 nomes coincidentes; `mcp.run()` final;
ausência de novos literais de credencial, token ou chave privada identificados
no diff/arquivos novos; `git diff --check` sem erros. A alteração de retorno
das sete listas para objetos de página é parte da consolidação de paginação;
os campos de sucesso dos itens permanecem preservados, exceto a sanitização
intencional de aliases aninhados.

`uv run pytest -q`: **411 passed in 2.19s**. A primeira execução encontrou
somente acesso negado ao cache local do uv; a execução com acesso autorizado
ao cache passou sem alteração de projeto/configuração. Os testes de protocolo
usam cliente em memória e dependências mockadas. Google/Workspace, MCP
funcional do host, DWD token exchange e IAM signJwt reais: **0 chamadas**.
HEAD permaneceu no baseline; staging, commit e push: **0**.

Ao executar a suíte novamente, acrescente uma evidência com data e contagem
atuais; não apague o contexto histórico sem uma razão.

## FASE 1.5 — WORKSPACE CONTENT & DEEP ANALYSIS — ROADMAP CURRENT

```text
FASE 1 — READ ADMIN                                        ✅ CONCLUÍDO
│
├── Directory / Calendar Resources / Reports                ✅ CONCLUÍDO
└── READ LAYER CONSOLIDATION                                ✅ CONCLUÍDO — 459 testes

FASE 1.5 — WORKSPACE CONTENT & DEEP ANALYSIS                ← EM ANDAMENTO
│
├── Architecture PLAN V1                                    ✅ CONCLUÍDO
├── Official Google Verification V1                          ✅ CONCLUÍDO / PASS
├── Foundation Implement V1                                  ✅ CONCLUÍDO — 487 testes
├── Foundation Review V1                                     ⚠️ BLOQUEADO — FR-P0 a FR-P3 preservados
├── Foundation Remediation Plan V1                           ✅ CONCLUÍDO
├── Foundation Remediation Implement V1                      ✅ CONCLUÍDO — 518 testes
├── Foundation Review V2                                     ⚠️ BLOQUEADO — FV2-P0 a FV2-P3 preservados
├── Foundation Remediation Plan V2                           ✅ CONCLUÍDO
├── Foundation Remediation Implement V2                       ✅ CONCLUÍDO / SEM COMMIT — 543 testes
├── Foundation Review V3                                     ⚠️ BLOQUEADO — FV3-P0 a FV3-P3 preservados
├── Foundation Remediation Plan V3                           ✅ CONCLUÍDO
├── Foundation Remediation Implement V3                      ✅ CONCLUÍDO / SEM COMMIT — 558 testes
├── Foundation Review V4                                     ⚠️ BLOQUEADO — FV4-P0 a FV4-P3 preservados
├── Foundation Remediation Plan V4                           ✅ CONCLUÍDO
├── Foundation Remediation Implement V4                      ✅ CONCLUÍDO / SEM COMMIT — 558 testes
├── Foundation Review V5                                     ✅ CONCLUÍDO — PASS / P0=0, P1=0, P2 bloqueante=0
├── Foundation Checkpoint V1                                ✅ CONCLUÍDO / CHECKPOINTED — commit deste change set
├── 1.5.1 Shared Drive Discovery                             ✅ CONCLUÍDO — RV2 / FINAL REVIEW V1 / CHECKPOINT V1
│   ├── PLAN V1                                             ✅ CONCLUÍDO — aprovado
│   ├── IMPLEMENT V1                                       ✅ CONCLUÍDO — 2 tools / sem Google
│   │   ├── workspace_drives_list                           ✅ CONCLUÍDO
│   │   ├── workspace_drive_get                             ✅ CONCLUÍDO
│   │   ├── catálogo MCP                                    ✅ CONCLUÍDO — 22 tools
│   │   ├── Content tools / Read / Write                     ✅ 2 / 20 / 0
│   │   ├── workspace_drive_files_list                       ⬜ AUSENTE — reservado para 1.5.2
│   │   ├── testes locais                                    ✅ CONCLUÍDO — sem Google/Auth
│   │   ├── Operational Auth Binding                         ✅ CONCLUÍDO — MCP TOML env configurado / lazy
│   │   ├── Content Research SA/IAM/DWD                      ✅ VALIDADO EM RV2 — cadeia keyless
│   │   ├── customer_id                                      ✅ CONFIGURADO — sem valor registrado
│   │   ├── RV1                                              ✅ HISTÓRICO — CONFIG precheck / 0 operações Google
│   │   ├── Diagnostic V1                                    ✅ CONCLUÍDO — boundary direta não herdava env MCP
│   │   ├── REAL VALIDATION RV2                              ✅ CONCLUÍDO — 1 chamada MCP / Drive API PASS
│   │   ├── FINAL REVIEW V1                                  ✅ CONCLUÍDO — 652 testes / scan seguro / docs sincronizados
│   │   └── CHECKPOINT V1                                    ✅ CONCLUÍDO — THIS COMMIT
│   └── próximo passo                                        ⬜ 1.5.2 — autorização explícita separada
├── 1.5.2 Drive File Inventory                               ✅ CONCLUÍDO — FINAL REVIEW V1
│   ├── PLAN V1                                             ✅ CONCLUÍDO
│   ├── IMPLEMENT V1                                       ✅ CONCLUÍDO — 1 tool / 747 testes / sem Google
│   ├── workspace_drive_files_list                          ✅ CONCLUÍDO
│   ├── catálogo MCP                                        ✅ CONCLUÍDO — 23 tools
│   ├── Content tools / Read / Write                         ✅ 3 / 20 / 0
│   ├── auth profile / scope                                 ✅ DRIVE_DISCOVERY / drive.readonly
│   ├── RV1                                                  ✅ HISTÓRICO — MCP_TRANSPORT_OR_CATALOG / 0 calls
│   ├── RV2                                                  ✅ PASS — 2 MCP calls / sem exposição sensível
│   ├── REAL VALIDATION                                     ✅ PASS
│   ├── FINAL REVIEW V1                                    ✅ CONCLUÍDO — 747 testes
│   ├── CHECKPOINT                                         ✅ CONCLUÍDO — THIS COMMIT
│   └── próximo gate                                         ⬜ WAIT FOR EXPLICIT AUTHORIZATION FOR NEXT CONTENT STAGE
├── 1.5.3 Content Reading Architecture & Safety              ✅ CONCLUÍDO — CHECKPOINT V1
│   ├── PLAN V1                                             ✅ CONCLUÍDO — arquitetura aprovada
│   ├── IMPLEMENT V1                                       ✅ CONCLUÍDO — substrate comum / 80 targeted / 827 regression / sem readers
│   ├── Content reading MCP tools                           ✅ 0
│   ├── cobertura por arquivo                               ✅ outcome terminal explícito obrigatório
│   ├── MIME routing / budgets / chunks / provenance        ✅ contratos internos fechados
│   ├── no-active-content policy                            ✅ NEVER EXECUTE FILE CONTENT
│   ├── REAL VALIDATION                                     ⬜ NOT APPLICABLE / NOT EXECUTED
│   ├── FINAL REVIEW V1                                    ✅ CONCLUÍDO — 80 targeted / 827 regression
│   ├── CHECKPOINT V1                                      ✅ CONCLUÍDO — substrate / sem SHA antecipado
│   └── próximo gate                                         ⬜ WAIT FOR EXPLICIT AUTHORIZATION FOR 1.5.4
├── 1.5.4 Google Docs Content                               ✅ CONCLUÍDO — CHECKPOINT V1 / IMPLEMENTAÇÃO FUNCIONAL E REVISÃO FINAL COMPLETAS
│   ├── PLAN V1                                             ✅ CONCLUÍDO
│   ├── IMPLEMENT V1                                       ✅ CONCLUÍDO — primeiro concrete reader / sem Google
│   ├── workspace_file_content_read                         ✅ CONCLUÍDO
│   ├── Docs structured read / tabs                         ✅ CONCLUÍDO
│   ├── Drive preflight/postflight / TOCTOU                 ✅ CONCLUÍDO
│   ├── upstream raw/decoded caps                            ✅ REMEDIADO — iter_raw + decode incremental bounded
│   ├── chunking / continuation                              ✅ CONCLUÍDO — store bounded/thread-safe
│   ├── partial resumível / coverage-gap terminal           ✅ CONCLUÍDO
│   ├── terminal failures / sectionBreak / HTTP 408          ✅ REMEDIADO
│   ├── capability / scope                                  ✅ GOOGLE_DOCS_CONTENT / drive.readonly
│   ├── catálogo MCP                                        ✅ 24 tools / Read 20 / Content 4 / Write 0
│   ├── Docs comments/comment threads                       ⬜ OUT OF SCOPE V1 — Developer Preview não solicitado
│   ├── PRE-RV REVIEW V1                                    ⚠️ BLOQUEADO — 6 findings materiais
│   ├── PRE-RV REMEDIATION V1                               ✅ CONCLUÍDO — 6 findings / 884 testes
│   ├── PRE-RV REMEDIATION V2                               ✅ CONCLUÍDO — recovery final / 885 testes
│   ├── PRE-RV RE-REVIEW V1                                 ⚠️ BLOQUEADO — RR-P2-01 / cobertura adversarial
│   ├── RR-P2-01 REMEDIATION V1                             ✅ CONCLUÍDO — test-only / 59 Docs / 897 regressão
│   ├── PRE-RV FINAL RE-REVIEW V1                            ✅ PASS
│   ├── Docs API enablement                                 ✅ CONFIRMADO PELO USUÁRIO
│   ├── REAL AUTH / TARGET RESOLUTION                       ✅ PASS — cadeia e snapshot sintético
│   ├── REAL VALIDATION V1                                  ⚠️ BLOQUEADO — metodologia de captura insuficiente
│   ├── REAL VALIDATION V2                                  ✅ CONCLUÍDO — EXTRACTION_FAILED / sem conteúdo persistido
│   ├── EXTRACTION FAILURE DIAGNOSTIC V1                    ✅ CONCLUÍDO — causa não retida / observabilidade insuficiente
│   ├── FAILURE OBSERVABILITY PLAN V1                       ✅ CONCLUÍDO — implementação autorizada
│   ├── FAILURE OBSERVABILITY IMPLEMENT V1                  ✅ CONCLUÍDO — LOCAL VALIDATION
│   ├── FAILURE OBSERVABILITY REMEDIATION V2                ✅ CONCLUÍDO — P2-01/P2-02 remediation / LOCAL VALIDATION (histórico)
│   ├── PRE-REAL OBSERVABILITY RE-REVIEW V2                 ⚠️ BLOQUEADO — um P2: P2-02 public/MCP coverage
│   ├── FAILURE OBSERVABILITY REMEDIATION V3                ✅ CONCLUÍDO — public/MCP 5/5 / local tests
│   ├── POST-REMEDIATION RE-REVIEW V3                       ⬜ PENDENTE — etapa histórica substituída pelos gates de localização/remediação abaixo
│   ├── REAL CONTENT VALIDATION V3                          ⚠️ BLOQUEADO — HISTÓRICO / superado pela localização causal posterior
│   │   ├── sectionBreak hypothesis                          ✅ REJEITADA — hardening local preservado; não é remediação funcional
│   │   └── classe causal específica                         ✅ CONCLUÍDO — HISTÓRICO / VT_000B identificado em gate real posterior
│   ├── STRUCTURAL RUNTIME FINGERPRINT PLAN V1              ✅ CONCLUÍDO
│   ├── STRUCTURAL RUNTIME FINGERPRINT IMPLEMENT V1         ✅ CONCLUÍDO — local only / enum fechado, propagation e boundaries testados
│   ├── REAL POST-REMEDIATION VALIDATION                    ✅ CONCLUÍDO — V1B / PROCESSED / 2 chunks / sem continuação
│   ├── REAL VALIDATION                                     ✅ CONCLUÍDO — leitor avançou além de VT_000B / sem TOCTOU
│   ├── control remediation Plan V1                         ✅ CONCLUÍDO — sem reparo estático genérico justificado
│   ├── private string failure reason diagnostic            ✅ CONCLUÍDO — 3 razões fechadas
│   ├── private control-range diagnostic                    ✅ CONCLUÍDO — seis faixas, removido após causa decisiva
│   ├── real control-range diagnostic                       ✅ CONCLUÍDO — VT_000B
│   ├── VT concrete reassessment                            ✅ CONCLUÍDO — VT→ASCII SPACE
│   ├── VT targeted implementation                          ✅ CONCLUÍDO — source span antes da normalização
│   ├── post-fix diagnostic cleanup plan / implementation    ✅ CONCLUÍDO — control_range removido; genéricos retidos
│   ├── documentação / roadmap                              ✅ CONCLUÍDO — V1B sanitizado / 190 focados / 1047 regressão
│   ├── functional implementation                           ✅ CONCLUÍDO — 1.5.4 funcionalmente pronta
│   ├── FINAL REVIEW V1                                     ✅ CONCLUÍDO — PASS / 0 findings bloqueantes / 0 não bloqueantes
│   ├── CHECKPOINT / COMMIT                                 ✅ ESTABELECIDO — este commit / `feat(content): complete Google Docs 1.5.4 reader`
│   └── próximo passo                                       ⬜ WAIT FOR EXPLICIT AUTHORIZATION — nenhuma próxima fase iniciada
├── Shared Drive Discovery / bounded Inventory               ← EM ANDAMENTO — implementação concluída / RV pendente
├── Google-native Content                                   ← EM ANDAMENTO — Google Docs 1.5.4 checkpointed / etapas seguintes aguardam autorização
├── Downloaded-file Extraction                              ⬜ PENDENTE
├── Gmail mailbox validation / Search                        ⬜ PENDENTE
├── Gmail message / Thread / Attachment Content              ⬜ PENDENTE
├── Cross-Workspace Research / Evidence                      ⬜ PENDENTE
├── Retrieval optimization / indexing                        ⬜ PENDENTE
└── Content Read Consolidation                              ⬜ PENDENTE

FASE 2 — WRITE / ADMINISTRATION                             ⬜ FUTURO
├── WRITE-LAYER-ARCHITECTURE-SAFETY-PLAN-V1                  ✅ PRESERVED
└── IMPLEMENTATION                                          ⚠️ PAUSED
```

### Foundation Implement V1

Implementação local concluída sem alterar o Read Layer existente:

- `content/auth/`: `ContentAuthProfile`, `WorkspaceSubject`, subject resolver
  protocol, closed scope registry e Content cache-key contract;
- `content/policy.py`: validação de customer, domínio, status e identidade;
- `content/operations.py`: allowlist positiva para `drive.list`, `drive.get` e
  `drive.files.list`, sem funções MCP;
- `content/transport.py`: `ContentReadTransport` mockável, GET-only, timeout,
  validação segura e retry bounded opt-in;
- `content/limits.py`: paginação e limites de bytes/caracteres/chunks;
- `content/evidence.py` e `content/audit.py`: referências determinísticas e
  eventos pseudonimizados, sem persistência;
- `http_errors.py`: códigos Content seguros integrados ao contrato existente;
- `tests/test_content_foundation.py`: 28 testes transversais;
- suíte completa: **487 passed = 459 baseline + 28 Foundation**;
- catálogo público: **20 tools**, Content tools: **0**;
- `server.py`, `config.py`, DWD, ADC e registration: preservados.

### Architecture PLAN V1 — decisões C1–C20 preservadas

| Decisão | Recomendação registrada | Consequência de implementação |
| --- | --- | --- |
| C1 | Content Layer exclusivamente Read/Audit | GET-only, scopes read-only e guard positivo |
| C2 | Auditor fixo `suporte.ti@cevalente.com.br` | auditor é política da aplicação; subject é separado |
| C3 | Subject dinâmico somente após Directory validation | JWT `sub` futuro será primary email canônico |
| C4 | Fan-out multi-mailbox explícito e bounded | confirmação de abrangência, batching, cancelamento |
| C5 | `drives_list`, `drive_get`, `drive_files_list` | `driveId` explícito; nenhum dump implícito |
| C6 | superfície Gmail mínima Read-only | `gmail.readonly` para conteúdo; metadata separado |
| C7 | APIs nativas antes de exportação/parsing | Docs/Sheets/Slides estruturados |
| C8 | payload/chunks explícitos | sem unlimited content ou auto-pagination |
| C9 | evidência mínima e rastreável | IDs, locators e referências, não payload bruto |
| C10 | minimização de PII/sensitive data | redaction, no raw dump, no local persistence default |
| C11 | retry somente Content Read idempotente | política separada do Write Layer |
| C12 | on-demand retrieval primeiro | índices full-text/vector deferred |
| C13 | audit event sanitizado | timestamp, operação, alvo pseudônimo, contagem, erro seguro |
| C14 | scopes mínimos read-only | registry fechado; nenhuma lista arbitrária |
| C15 | Content Research SA/DWD separado | recomendado; sem provisionamento nesta entrega |
| C16 | primeiro vertical Shared Drive | discovery + bounded inventory |
| C17 | primeiro delivery D2 | `drives_list` + `drive_get` + `drive_files_list` |
| C18 | Real Validation incremental | RV1–RV9; nenhuma executada nesta entrega |
| C19 | sequência por camadas | foundation → Drive → native content → Gmail → research |
| C20 | deployment remoto deferido | local stdio permanece atual |

### Official Google Verification V1 — fatos e pendências preservados

Fatos verificados oficialmente: Drive API v3; `drives.list` com
`drive.readonly`; `files.list` bounded com `corpora=drive`, `driveId`,
`includeItemsFromAllDrives=true`, `supportsAllDrives=true`, `spaces=drive` e
`trashed=false`; `fullText` é busca indexada do Drive, não semantic/vector
search; DWD usa email do usuário no `sub`; Docs/Sheets/Slides possuem APIs
read-only estruturadas; Gmail `gmail.readonly` cobre leitura de mensagens,
threads e attachments; Gmail não oferece endpoint documentado de pesquisa
domain-wide; Vault é arquitetura separada.

Permanecem `OFFICIAL DOC VERIFICATION REQUIRED` / `REQUIRES REAL VALIDATION`:

- estado real de APIs, DWD, scopes, privilégios e customer ID;
- comportamento de subjects suspensos, arquivados, excluídos, aliases e
  identidades externas;
- lifecycle definitivo de `driveId`, cobertura completa de `fullText`, limites
  de download e matriz de export MIME;
- limites de payload de Docs/Slides, MIME edge cases de Gmail e `Retry-After`;
- acesso real ao Shared Drive e quotas efetivas do projeto.

### FOUNDATION REVIEW V1 — 14/09/2026

Resultado: **BLOCKED**. Foram preservados os achados FR-P0-01 a FR-P3-02:
broker Content ausente, provisioning não confiável, field masks e caps de
paginação/retry incompletos, exposição de `httpx.Response`, `q` livre,
mailbox readiness sem capability, client HTTP injetável e modelos de
evidência/auditoria com campos livres. Nenhuma correção foi feita no review.

### FOUNDATION REMEDIATION PLAN V1 — 14/09/2026

**COMPLETE.** O plano selecionou broker separado da DWD histórica, factory +
registry fechado, field masks internas, caps por operação, filtros
estruturados, client controlado e HMAC para pseudonimização. Shared Drive,
Gmail, Directory resolver real e aquisição de token permaneceram fora do
escopo.

### FOUNDATION REMEDIATION IMPLEMENT V1 — 14/09/2026

**COMPLETE / SEM COMMIT.** FR-P0-01, FR-P0-02, FR-P1-01 a FR-P1-04,
FR-P2-01 a FR-P2-04 e FR-P3-01/FR-P3-02 foram remediados localmente. O
resultado foi verificado com testes direcionados e regressão completa. O
broker não gera token; o registry não pressupõe Content SA/DWD; o transport
não executa requests nos testes; nenhuma tool MCP foi adicionada.

Próximo passo obrigatório: **FOUNDATION REVIEW V2**. O checkpoint/commit está
pendente de autorização e de Review V2 aprovado.

### FOUNDATION REVIEW V2 — 14/09/2026

Resultado preservado: **BLOCKED**. A revisão independente encontrou resíduos
de provenance de profile/subject, bypass operation→transport, `max_items`
meramente declarativo, mailbox readiness não aplicada pelo broker, payload JSON
genérico, retry classificável pelo caller, ausência de ceiling absoluto de
contexto e cobertura adversarial insuficiente. Nenhuma correção foi executada
na Review V2.
IDs preservados: **FV2-P0-01**, **FV2-P0-02**, **FV2-P1-01**,
**FV2-P1-02**, **FV2-P1-03**, **FV2-P2-01**, **FV2-P2-02** e
**FV2-P3-01**; os resíduos relacionados **FR-P0-01**, **FR-P0-02**,
**FR-P1-02**, **FR-P1-03**, **FR-P2-02** e **FR-P3-01** também permanecem
registrados no histórico da remediação.

### FOUNDATION REMEDIATION PLAN V2 — 14/09/2026

**COMPLETE.** O plano selecionou authorities opacas vinculadas ao issuer,
provenance verificada por membership, broker obrigatório, matriz fechada de
capabilities, resultados Drive tipados, enforcement de `max_items`, retry
conservador e ceilings absolutos. Directory lookup real, token broker Google,
Shared Drive MCP tools, Gmail e Write permanecem fora do escopo.

### FOUNDATION REMEDIATION IMPLEMENT V2 — 14/09/2026

**COMPLETE / SEM COMMIT.** A cadeia `profile handle → subject handle → broker
context → transport → typed result` foi aplicada localmente. Os contratos
internos de `drive.list`, `drive.get` e `drive.files.list` continuam GET-only,
com field masks fechadas, `trashed=false`, paginação de uma página e sem
continuação inventada. `max_items` participa do `pageSize`; respostas acima
do limite são rejeitadas. O transport mantém client de produção controlado,
redirects desativados e MockTransport somente no wiring de testes.

Os testes direcionados da Foundation passaram em **84 testes** e a regressão
completa passou em **543 testes** (518 preexistentes preservados + 25 testes
adicionais desta remediação). `server.py`, `config.py`, DWD histórico e
registro MCP permaneceram intactos; catálogo público: 20 tools, Content: 0,
Write: 0. Nenhuma chamada Google, token, DWD, IAM `signJwt`, alteração Cloud,
Admin Console, scope, Service Account, staging, commit ou push foi executada.

Próximo passo obrigatório: **FOUNDATION REVIEW V3**. O checkpoint/commit não
é permitido antes da revisão independente e de autorização explícita.

### FOUNDATION REVIEW V3 — 14/09/2026

Resultado preservado: **BLOCKED**. A revisão adversarial identificou authority
baseada em estado de issuer mutável, possibilidade de bypass por
subclass/duck typing, caminhos internos que ainda devolviam
`httpx.Response`/JSON genérico, injeção de client fora de harness isolado,
aceitação de `trashed=true` no resultado tipado, identificador textual livre
em erros Content e cobertura adversarial incompleta. Nenhuma correção foi
executada na Review V3.

IDs preservados: **FV3-P0-01**, **FV3-P0-02**, **FV3-P1-01**,
**FV3-P1-02**, **FV3-P2-01**, **FV3-P2-02** e **FV3-P3-01**; os resíduos
relacionados **FR-P0-01**, **FR-P0-02**, **FR-P1-04**, **FR-P2-01**,
**FR-P2-03** e **FR-P3-01** também permanecem registrados no histórico.

### FOUNDATION REMEDIATION PLAN V3 — 14/09/2026

**COMPLETE.** O plano selecionou kernel de authority lexicalmente encapsulado,
handles opacos sem dados, membership fraco por identidade e sentinel oculto;
bootstrap sem parâmetros, runtime selado, adapter HTTP específico por operação,
resultados tipados e identificadores fechados de erro. Processo isolado,
autenticação Google real, Directory lookup e tools MCP permaneceram fora do
escopo.

### FOUNDATION REMEDIATION IMPLEMENT V3 — 14/09/2026

**COMPLETE / SEM COMMIT.** A autoridade local passou a ser emitida e verificada
por um kernel closure-owned capturado pelo runtime. Handles fabricados,
copiados ou oriundos de outro runtime não autorizam. `ContentRuntime.execute()`
é a única fachada operacional; profile, resolver, broker, contexto e adapter
HTTP permanecem internos e não substituíveis pela API suportada. O bootstrap
de produção não aceita parâmetros e falha fechado enquanto o provisioning real
não existe.

Os antigos caminhos `_request()`, `_request_json()`, `_for_test()` e
`_attach_internal_client()` foram removidos. Cada contrato Drive Foundation
executa GET fixo, parseia a resposta diretamente para DTO específico e não
expõe response, headers, body ou JSON genérico. `drive.files.list` exige
`trashed is False` também na resposta. Erros Content usam operação fechada e
não refletem texto fornecido pelo caller.

Os testes direcionados passaram em **99 testes** e a regressão completa passou
em **558 testes**, preservando os 543 testes anteriores. O catálogo público
permanece com 20 tools; Content: 0; Write: 0. Nenhuma chamada Google, Drive,
Gmail, Docs, Sheets, Slides, Directory ou MCP funcional; nenhum token, DWD,
IAM `signJwt`, ADC, alteração Cloud/Admin Console/IAM/scope/Service Account,
staging, commit ou push foi executado.

Próximo passo obrigatório: **FOUNDATION REVIEW V4**. O checkpoint/commit
continua pendente de revisão independente aprovada e autorização explícita.

### FOUNDATION REVIEW V4 — 14/09/2026

Resultado: **BLOCKED**. A revisão independente identificou trust root e broker
alternativos, fabricação/subclassificação de `ContentRuntime`, execução por
adapter/client/request normalizado arbitrário, bypass de subclasses em limites
e retry, canal textual em auditoria e cobertura adversarial insuficiente.

IDs preservados: **FV4-P0-01**, **FV4-P0-02**, **FV4-P1-01**,
**FV4-P2-01**, **FV4-P2-02** e **FV4-P3-01**. Nenhuma correção foi executada
na Review V4.

### FOUNDATION REMEDIATION PLAN V4 — 14/09/2026

**COMPLETE.** O plano delimitou a boundary suportada a inputs MCP/runtime e à
API Content, reconheceu execução Python arbitrária como fora do threat model,
removeu o binder de callable, fechou a operação HTTP, moveu a composição para o
startup root, revalidou limites no consumo e fechou categorias de auditoria.

### FOUNDATION REMEDIATION IMPLEMENT V4 — 14/09/2026

**COMPLETE / SEM COMMIT.** A implementação removeu o runtime subclass token e o
`_bind_content_runtime`, eliminou fábricas module-level de authority, tornou o
normalized request data-only e fez o adapter reconstruir host/path/método/query
a partir de operações Drive fechadas. `ContentRuntime` agora é uma façade
concreta montada por services internos, sem setters, attach de client ou
executor caller-supplied.

Policies de paginação, contexto e retry passaram a rejeitar subclasses e a
revalidar hard caps no consumo. `AuditScopeSummary.operation` e
`AuditEvent.operation` usam identificadores fechados. Resultados continuam
tipados, `trashed is False` continua obrigatório e não há caminho operacional
para response/JSON genérico.

O threat model registrado é:

```text
IN SCOPE:  untrusted MCP/runtime inputs; supported Content API
OUT:       arbitrary Python execution inside the MCP process,
           post-compromise monkeypatch/introspection, debugger/memory
           manipulation e deliberate closure mutation
```

A suíte local passou em **558 testes** após a implementação. O catálogo
permanece com 20 tools, Content = 0 e Write = 0. Nenhuma chamada Google,
Directory, Drive, Gmail, Docs, Sheets, Slides ou MCP funcional foi realizada;
nenhum token, DWD, IAM `signJwt`, ADC, alteração administrativa, staging,
commit ou push foi executado.

Próximo passo obrigatório: **FOUNDATION REVIEW V5**. O checkpoint/commit
continua pendente de revisão independente aprovada e autorização explícita.

### P0 resolution matrix

| Finding | Estado após verificação/foundation | Bloqueio restante |
| --- | --- | --- |
| F-P0-01 APIs/scopes/DWD | contratos oficiais verificados; estado externo não alterado | bloqueia primeiro Drive/Gmail até setup manual e RV |
| F-P0-02 subject/scopes arbitrários | boundary, profile, validator e registry implementados | Directory-backed resolver e token broker ainda pendentes |
| F-P0-03 mutation barrier | guard positivo, GET-only transport e registry implementados | deve ser preservado em cada futura tool |

### Manual Google changes and validation

Nenhuma mudança manual foi executada naquele checkpoint. Content SA/DWD não
foi criado, scopes não foram adicionados, APIs não foram habilitadas e Drive
RV1 não foi executada. O requisito então pendente foi superado somente pela
implementação local 1.5.1 descrita abaixo; setup manual e RV1 continuam
pendentes.

### 1.5.1 SHARED DRIVE DISCOVERY — IMPLEMENT V1 — 15/09/2026

**COMPLETE / LOCAL ONLY.** O PLAN V1 aprovado foi convertido em duas tools
MCP públicas: `workspace_drives_list` e `workspace_drive_get`. O catálogo local
passou a 22 tools únicas — 20 Read históricas, 2 Content e 0 Write — e
`workspace_drive_files_list` continua ausente, reservado ao inventário 1.5.2.

Os contratos usam requests e resultados tipados da Foundation, página única,
limites 1–100, default 25, `max_items` 100, fields fechadas, endpoints HTTPS
fixos, GET-only, redirects desabilitados e retry conservador. Shared Drive
names são atributos de display; drive IDs são identificadores operacionais
estáveis e nomes duplicados são preservados. `useDomainAdminAccess` permanece
false por default e exige capability administrativa explícita antes do HTTP.

Foi adicionada somente estrutura local de configuração Content sob
`content/config.py` e um provider keyless com ports/fakes locais, cache RAM-only,
expiry bounded e erros redacted. Não há Content Research SA, DWD, IAM, ADC,
token, JWT, chamada Google, configuração Cloud/Admin Console ou validação real
nesta entrega. A cadeia futura permanece
`ADC -> IAM signJwt -> DWD -> OAuth -> Drive API`, separada da identidade Read
histórica e limitada ao scope
`https://www.googleapis.com/auth/drive.readonly`.

O threat model da Foundation foi preservado exatamente: inputs MCP/runtime não
confiáveis e API Content suportada estão no escopo; execução arbitrária de
Python no processo, monkeypatch/introspecção pós-comprometimento,
debugger/memória e mutação deliberada de closures estão fora do escopo.

Testes locais novos cobrem catálogo/schema MCP, duplicate names, stable IDs,
paginação e limites, path segment, admin authorization, fields/host/GET,
respostas desconhecidas/malformadas, raw/token redaction, mutation barrier,
provider keyless com fakes e regressão da Read Layer. A suíte final confirmou
**629 testes aprovados**, sem chamada externa.

#### Próximo gate

```text
PLAN V1                         ✅ CONCLUÍDO
IMPLEMENT V1                   ✅ CONCLUÍDO
REAL VALIDATION RV2            ✅ CONCLUÍDO — evidência hospedada pelo MCP preservada abaixo
```

Antes de qualquer command que requeira `gcloud auth application-default
login`, o operador deve autorizar explicitamente. O Codex deve parar, fornecer
o comando exato e aguardar se a ADC estiver expirada. A RV1 futura será uma
única consulta bounded `workspace_drives_list`, sem retry, paginação adicional,
conteúdo de arquivo ou mutação.

### 1.5.1 SHARED DRIVE DISCOVERY — OPERATIONAL AUTH BINDING IMPLEMENT V1 — 15/09/2026

**COMPLETE / LOCAL ONLY.** O binding operacional foi implementado sob a camada
Content sem alterar a arquitetura Read histórica. A configuração é composta
por cinco variáveis process-only não secretas: project ID, Content Research
Service Account, subject, customer ID e domínio. O scope continua fechado em
`https://www.googleapis.com/auth/drive.readonly`; não existe variável de scope
nem fallback `my_customer`.

O bootstrap permanece lazy: import, startup, catálogo e parsing de
configuração não executam ADC. A cadeia futura é
`ADC -> IAM signJwt -> DWD -> OAuth -> Drive API`; os adapters produtivos
somente são chamados quando uma operação Content precisa de token. ADC, IAM,
DWD, OAuth e Drive não foram executados nesta entrega.

O operador confirmou manualmente Content SA, IAM Token Creator e DWD
`drive.readonly`. Esses fatos não foram verificados em runtime. O customer ID
continua obrigatório e deve ser fornecido antes da RV1. O resultado local foi
verificado com **652 testes aprovados**, sem falhas, usando somente fakes e
`httpx.MockTransport` para os caminhos externos.

#### Próximo gate

```text
OPERATIONAL AUTH BINDING IMPLEMENT V1 = COMPLETE
CUSTOMER ID                          = CONFIGURED IN MCP ENV
RV1                                  = CONFIG PRECHECK FAILURE / 0 GOOGLE OPERATIONS
DIAGNOSTIC V1                        = MCP EXECUTION-BOUNDARY ROOT CAUSE
RV2                                  = PASS / 1 MCP-HOSTED OPERATION
FINAL REVIEW V1                      = PASS
CHECKPOINT V1                        = COMPLETE / THIS COMMIT
```

Antes de qualquer comando que requeira `gcloud auth application-default login`,
é obrigatório parar e solicitar autorização explícita do operador.

### 1.5.1 SHARED DRIVE DISCOVERY — RV1 / DIAGNOSTIC V1 / RV2 / FINAL REVIEW V1 — 15/09/2026

```text
RV1
├── CONFIG precheck                                      ✅ FALHOU — histórico preservado
└── operações Google funcionais                           ✅ 0

DIAGNOSTIC V1
├── config.toml / MCP env / ContentConfig                ✅ CORRETOS
├── profile provisioning / subject construction           ✅ PASS
└── causa                                                 ✅ boundary Python/PowerShell não herdava env MCP

RV2
├── boundary                                               ✅ MCP HOSTED
├── chamada funcional                                     ✅ EXATAMENTE 1 — workspace_drives_list
├── CONFIG / ADC / IAM signJwt / DWD OAuth / Drive API    ✅ PASS
├── drives retornados / próxima página                    ✅ 1 / PRESENTE
├── admin mode / retries / paginação                      ✅ false / 0 / 0
└── mutações / exposição sensível                         ✅ 0 / 0

FINAL REVIEW V1
├── contratos, keyless security e boundary MCP            ✅ PASS
├── regressão local                                       ✅ 652 passed
├── documentação                                          ✅ SYNCHRONIZED
├── checkpoint V1                                         ✅ CONCLUÍDO — THIS COMMIT
└── próximo gate                                          ⬜ 1.5.2 — autorização explícita separada
```

### 1.5.2 DRIVE FILE INVENTORY — PLAN V1 / IMPLEMENT V1 — 15/09/2026

PLAN V1 = **COMPLETE** e IMPLEMENT V1 = **COMPLETE / LOCAL ONLY**. Foi
registrada exatamente uma nova tool, `workspace_drive_files_list`, elevando o
catálogo para 23 tools únicas: 20 Read históricas, 3 Content e 0 Write. A Read
Layer permaneceu semanticamente inalterada, `mcp.run()` continuou como operação
final absoluta e não há rota Content de mutação nem scope de escrita.

A tool usa contrato fechado de quatro parâmetros, página única, hard cap 500,
request fixo para `Drive files.list`, `q=trashed = false`, fields allowlisted e
DTO mínimo. `trashed` deve ser `false` em cada item, `size` aceita apenas string
int64 não negativa e folders permanecem itens identificados por MIME. A regra
interna anterior `DRIVE_METADATA / drive.metadata.readonly` foi alinhada ao
profile operacional existente `DRIVE_DISCOVERY / drive.readonly`, sem mudança
externa de Google, DWD, IAM, Service Account ou das cinco variáveis.

Testes dedicados: **94 passed**. Regressão completa: **747 passed**, apenas com
mocks/fakes. RV1 permanece registrada como `MCP_TRANSPORT_OR_CATALOG` com zero
chamadas por catálogo stale. RV2 passou com exatamente duas chamadas MCP:
discovery retornou um Drive e token presente; inventory retornou um arquivo e
token presente; invariant de resposta passou. Google activity adicional = 0,
ADC activity = 0, retries = 0, continuação = 0 e valores sensíveis expostos = 0.

REAL VALIDATION = **PASS**. FINAL REVIEW V1 = **COMPLETE**. CHECKPOINT V1 =
**COMPLETE / THIS COMMIT**; o SHA não é antecipado neste registro. PHASE STATUS
= SYNCHRONIZED.

Próximo gate: **WAIT FOR EXPLICIT AUTHORIZATION FOR NEXT CONTENT STAGE**.

### 1.5.4 GOOGLE DOCS CONTENT — PLAN V1 / IMPLEMENT V1 — 16/09/2026

PLAN V1 = **COMPLETE** e IMPLEMENT V1 = **COMPLETE / LOCAL ONLY**. Foi
registrada exatamente uma nova tool, `workspace_file_content_read`, elevando o
catálogo para 24 tools únicas: 20 Read históricas, 4 Content e 0 Write. A Read
Layer e as três tools Content anteriores permaneceram semanticamente isoladas;
`mcp.run()` continua como operação final absoluta.

O primeiro reader concreto usa `documents.get` fechado com tabs, suggestions
inline e field mask interna. Drive metadata preflight/postflight protege MIME,
`modifiedTime` e `trashed`; somente depois do postflight chunks são liberados.
O fetch Docs possui cap hard de 32 MiB independente do output MCP. Traversal,
normalização, tables, headers/footers/footnotes, provenance, chunking e
continuation são locais e bounded. Objetos visuais/equations/unknown textual
structures produzem coverage gap parcial explícito; comments Developer Preview
estão fora do escopo e não são solicitados.

A capability `GOOGLE_DOCS_CONTENT` reutiliza exclusivamente
`DRIVE_DISCOVERY / drive.readonly`. Não foi adicionado scope OAuth, DWD, IAM,
Service Account, variável de ambiente, parser dependency, export, download,
OCR, mutation route ou Write scope. O status de `docs.googleapis.com` é
UNKNOWN e qualquer enablement futuro permanece ação manual do usuário.

Os testes do IMPLEMENT foram exclusivamente sintéticos, com fakes e
`httpx.MockTransport`; nenhuma atividade Google, ADC, IAM ou OAuth ocorreu. Os
gates registraram **33 passed** no reader Google Docs, **84 passed** no
substrate 1.5.3, **172 passed** em Shared Drive + Drive Inventory + Operational
Auth, **207 passed** em Foundation/security/protocol e **864 passed** na
regressão completa. REAL VALIDATION = **NOT EXECUTED**; FINAL REVIEW = **NOT
EXECUTED**; CHECKPOINT = **NOT EXECUTED**.

PRE-RV REVIEW V1 = **BLOCKED** preserva os seis findings materiais. PRE-RV
REMEDIATION V1/V2 = **COMPLETE**: recepção raw e decoding possuem caps
independentes de 32 MiB, failures terminais não aceitam chunks/resultados,
continuation é thread-safe e bounded, HTTP 408 esgotado vira
`TRANSIENT_UPSTREAM`, e `sectionBreak` preserva provenance location-only sem
texto inventado. Os gates finais V2 registraram **21 casos específicos**, **47
Google Docs**, **91 substrate**, **54 Shared Drive**, **94 Drive Inventory**,
**24 Operational Auth**, **207 Foundation/security/protocol** e **885 passed**
na regressão completa.

PRE-RV RE-REVIEW V1 = **BLOCKED — RR-P2-01** identificou exclusivamente a
ausência de testes versionados para integridade adversarial de gzip/deflate,
Content-Encoding empilhado e o limite raw exato. RR-P2-01 REMEDIATION V1 =
**COMPLETE** adicionou somente testes: **12 RR-P2-01**, **21 remediação
anterior**, **59 Google Docs**, **91 substrate**, **54 Shared Drive**, **94
Drive Inventory**, **24 Operational Auth**, **207 Foundation/security/protocol**
e **897 passed** na regressão completa. Source de produção permaneceu
inalterado naquela entrega. PRE-RV FINAL RE-REVIEW V1 = **PASS**; a validação
real e o checkpoint ainda permaneciam pendentes naquele ponto histórico.

Próximo gate histórico: **WAIT FOR EXPLICIT PRE-RV FINAL RE-REVIEW AUTHORIZATION**.
Não iniciar 1.5.5.

### 1.5.4 GOOGLE DOCS CONTENT — FAILURE OBSERVABILITY IMPLEMENT V1 — 17/09/2026

**COMPLETE / LOCAL VALIDATION / SEM GOOGLE.** A implementação autorizada
adicionou `FailureStage`, enum fechado com dez localizações causais, ao
`ProcessingOutcome`, preservando a separação entre `processing_status`
(resultado terminal), `safe_error_code` (o que falhou) e `failure_stage` (onde
falhou). O campo é `null` em `PROCESSED`, `EMPTY` e `PARTIALLY_PROCESSED`, e só
é preenchido em falhas terminais quando o boundary consegue determinar o
estágio com segurança.

Os stages foram propagados nos boundaries reais de preflight, request/resposta
Docs, parse JSON/schema, extração estrutural, provenance e postflight. O
serializer MCP mantém a representação `dict → TextContent JSON` sem mensagens
de exceção, URLs, IDs, tokens ou conteúdo; o modelo de audit aceita somente o
enum/null e mantém a pseudonimização HMAC. Outcomes, budgets, retry, scopes,
capabilities e a quantidade de tools não foram alterados.

Os testes sintéticos cobrem os dez stages quando distinguíveis, regressões de
sucesso/empty/partial, invariantes de falha terminal, serialização MCP e
leakage de sentinelas. A validação local desta implementação foi concluída sem
ADC, IAM, OAuth, Drive ou Docs reais. A V1 anterior permanece registrada como
`EXTRACTION_FAILED` com metodologia de captura insuficiente; a validação real
pós-remediação continua **PENDING**.

#### Estado e próximo gate

```text
PRE-RV FINAL RE-REVIEW V1                 ✅ PASS
REAL AUTH                                 ✅ PASS — histórico preservado
TARGET RESOLUTION                         ✅ PASS — histórico preservado
REAL VALIDATION V1                        ⚠️ BLOQUEADO — captura insuficiente
REAL VALIDATION V2                        ✅ EXTRACTION_FAILED — histórico preservado
EXTRACTION FAILURE DIAGNOSTIC V1          ✅ COMPLETE
FAILURE OBSERVABILITY PLAN V1             ✅ COMPLETE
FAILURE OBSERVABILITY IMPLEMENT V1        ✅ COMPLETE — LOCAL VALIDATION
REAL POST-REMEDIATION VALIDATION          ⬜ PENDING
FINAL REVIEW                              ⬜ NOT EXECUTED
CHECKPOINT                                ⬜ NOT EXECUTED
PRÓXIMO GATE                              ⬜ PRE_REAL_VALIDATION_REVIEW_FAILURE_OBSERVABILITY_V1
```

PHASE STATUS = **SYNCHRONIZED**.

### 1.5.4 GOOGLE DOCS CONTENT — FAILURE OBSERVABILITY REMEDIATION V2 — 17/09/2026

**COMPLETE / LOCAL VALIDATION / SEM GOOGLE.** A remediation cirúrgica corrigiu
os dois achados P2 do PRE-REAL OBSERVABILITY REVIEW V1: os estados correntes
de `README.md` e `docs/02_MCP_CATALOG.md` foram atualizados sem apagar
histórico, e os testes existentes foram reforçados para atravessar os cinco
sentinelas sintéticos pelos boundaries MCP, audit e exceção segura. Nenhuma
alteração funcional de produção, autenticação, escopo, catálogo ou configuração
foi feita.

Os testes locais permanecem verdes, a validação real pós-remediação continua
**PENDENTE**, e 1.5.4 não está concluída. Não houve Google, ADC, IAM, OAuth,
staging, commit, push ou checkpoint.

#### Estado e próximo gate

```text
P2-01 DOCUMENTATION                         ✅ RESOLVIDO
P2-02 ADVERSARIAL LEAKAGE COVERAGE          ✅ RESOLVIDO — LOCAL TESTS
FAILURE OBSERVABILITY REMEDIATION V2        ✅ COMPLETE — LOCAL VALIDATION
REAL POST-REMEDIATION VALIDATION            ⬜ PENDING
FINAL REVIEW                                ⬜ NOT EXECUTED
CHECKPOINT                                  ⬜ NOT EXECUTED
PRÓXIMO GATE                                ⬜ PRE-REAL-OBSERVABILITY-RE-REVIEW V2
```

PHASE STATUS = **SYNCHRONIZED**.

### 1.5.4 GOOGLE DOCS CONTENT — PRE-REAL OBSERVABILITY RE-REVIEW V2 / REMEDIATION V3 — 17/09/2026

O PRE-REAL OBSERVABILITY RE-REVIEW V2 foi **BLOQUEADO por um único P2,
P2-02**: a cobertura anterior provava os cinco sentinelas nos caminhos de
audit e exceção, mas não os injetava genuinamente nos caminhos de resultado
público e MCP; a força adversarial era apenas **PARTIAL**. P2-01 de
documentação permaneceu resolvido. Nenhuma correção foi feita durante o
re-review.

A REMEDIATION V3 foi **IMPLEMENTADA / VALIDADA LOCALMENTE** somente nos
testes MCP. Cada um dos cinco valores sintéticos é levantado dentro de uma
falha upstream sintética real do `httpx.MockTransport`, atravessa o tradutor
seguro existente, produz resultado público com classificação segura e passa
pelo boundary real `Client → TextContent → JSON`. A cobertura local agora é
5/5 em public, MCP, audit e exception, sem leakage e com
`processing_status`, `safe_error_code` e `failure_stage` preservados quando
aplicáveis. Source funcional permaneceu inalterado.

#### Estado e próximo gate

```text
PRE-REAL OBSERVABILITY RE-REVIEW V2       ⚠️ BLOCKED — one P2 (P2-02)
P2-02 PUBLIC/MCP COVERAGE                 ✅ REMEDIATION V3 IMPLEMENTED — LOCAL TESTS
V3 public sentinel coverage               ✅ 5/5
V3 MCP TextContent/JSON coverage          ✅ 5/5
audit sentinel coverage                   ✅ 5/5 — preservada
exception sentinel coverage               ✅ 5/5 — preservada
post-remediation re-review                ⬜ PENDING
real Google content validation             ⬜ PENDING
1.5.4 overall                              ⬜ NOT COMPLETE
CHECKPOINT                                 ⬜ NOT COMPLETE
PRÓXIMO GATE                               ⬜ PRE_REAL_OBSERVABILITY_FINAL_RE_REVIEW_V3
```

PHASE STATUS = **SYNCHRONIZED**.

### 1.5.4 GOOGLE DOCS CONTENT — STRUCTURAL RUNTIME FINGERPRINT IMPLEMENT V1 — 18/09/2026

**COMPLETE / LOCAL VALIDATION / SEM GOOGLE.** A instrumentação autorizada
adicionou `StructuralFailureKind`, enum fechado com onze classes causais, ao
contrato seguro `ContentSafeError → ProcessingOutcome → public dict → MCP
TextContent JSON`. O fingerprint só pode ser um enum tipado e só é válido
quando `failure_stage=DOCS_STRUCTURAL_EXTRACTION`; outcomes estruturais sem
fingerprint e combinações fora desse stage falham fechado.

Os boundaries reais cobertos são traversal de tabs, dispatch estrutural do
body, estrutura de parágrafo, índices/ranges de elementos de parágrafo,
estrutura de tabela, células, TOC, headers, footers, footnotes e validação
estrutural residual. `PROVENANCE_BUILD` permaneceu isolado com fingerprint
`null`; `content/audit.py` não foi alterado conforme o PLAN. A semântica de
`processing_status`, `safe_error_code` e `failure_stage` permaneceu inalterada.

Os testes locais sintéticos exercitam cada uma das onze fronteiras pelo
extractor real, propagation segura, nullability, combinações inválidas,
serialização pública/MCP e leakage adversarial. O hardening de `sectionBreak`
confirma extração para `endIndex=1` sem `startIndex` e para
`startIndex=0`; a hipótese de que este campo era a causa da falha real é
**REJEITADA**. Não houve correção funcional de parágrafo, tabela, TOC, tabs,
headers, footers, footnotes ou validação estrutural.

Os gates focais registraram 12 testes de fingerprint causal/propagation, 1 de
serialização MCP, 1 de leakage e 2 de sectionBreak; a regressão completa
terminou em **927 passed**, sem Google, ADC, IAM ou OAuth.

```text
REAL CONTENT VALIDATION V3                         ⚠️ BLOQUEADO — DOCS_STRUCTURAL_EXTRACTION
sectionBreak hypothesis                            ✅ REJEITADA — regression hardening somente
STRUCTURAL RUNTIME FINGERPRINT PLAN V1             ✅ COMPLETE
STRUCTURAL RUNTIME FINGERPRINT IMPLEMENT V1        ✅ COMPLETE — LOCAL VALIDATION
next real validation                               ⬜ PENDING
1.5.4 overall                                      ⬜ NOT COMPLETE
CHECKPOINT                                          ⬜ NOT EXECUTED
PRÓXIMO GATE                                        ⬜ PRE_REAL_STRUCTURAL_FINGERPRINT_REVIEW_V1
```

PHASE STATUS = **SYNCHRONIZED**.

### 1.5.4 GOOGLE DOCS CONTENT — PARAGRAPH RUNTIME FINGERPRINT IMPLEMENT V1 — 18/09/2026

**COMPLETE / LOCAL VALIDATION / SEM GOOGLE.** A observabilidade subordinada à
falha estrutural real foi implementada sem alterar a semântica do parser.
`ParagraphFailureKind` é uma taxonomia fechada de oito boundaries e permanece
estritamente aninhada em `structural_failure_kind=PARAGRAPH_STRUCTURE`.
`PARAGRAPH_ELEMENT_INDEX` e `PROVENANCE_BUILD` preservam seus caminhos próprios
e não recebem fingerprint de parágrafo.

Os oito boundaries de `_Extractor._paragraph` atravessam o mecanismo seguro
`ContentSafeError → ProcessingOutcome → public dict → MCP TextContent JSON`.
Testes locais causais cobrem cada enum, preservação de erro filho,
nullability/combinações inválidas e leakage adversarial. Não houve correção
funcional de metadados, unions, texto, limites, normalização ou provenance; o
`content/audit.py` permaneceu inalterado.

Os gates focais registraram **8** fingerprints causais de parágrafo, **1** de
preservação do fingerprint filho, **15** testes de nullability/invariants, **2**
de serialização MCP e **1** de leakage específico. A regressão completa
terminou em **946 passed**, sem Google, ADC, IAM ou OAuth.

```text
REAL V4B                                           ⚠️ EXTRACTION_FAILED
structural_failure_kind                            ✅ PARAGRAPH_STRUCTURE
paragraph diagnostic V1                            ✅ INSUFFICIENT_EVIDENCE
ParagraphFailureKind PLAN                          ✅ COMPLETE
ParagraphFailureKind IMPLEMENT                    ✅ COMPLETE — CURRENT LOCAL STATE
next real paragraph fingerprint validation         ⬜ PENDING
1.5.4 overall                                      ⬜ NOT COMPLETE
PRÓXIMO GATE                                        ⬜ PRE_REAL_PARAGRAPH_FINGERPRINT_REVIEW_V1
```

PHASE STATUS = **SYNCHRONIZED**.

### 1.5.4 GOOGLE DOCS CONTENT — POST-REAUTH RECOVERY / ELEMENT STRUCTURE DIAGNOSTIC SUBSTRATE V1 — 20/09/2026

Os marcos imutáveis anteriores permanecem históricos: REAL V4B retornou
`EXTRACTION_FAILED` em `DOCS_STRUCTURAL_EXTRACTION / PARAGRAPH_STRUCTURE`; a
implementação e a revisão local de `ParagraphFailureKind` foram concluídas com
**946 passed**. A interrupção inicial da V5 decorreu de `WSAEACCES` 10013 no
ambiente Codex e, depois, de `ADC_REFRESH` no MCP hospedado. O diagnóstico de
sentinela fixa classificou `REAUTH_REQUIRED`; a rede do host manual permaneceu
saudável. O operador concluiu `gcloud auth application-default login`, a
validação isolada da ADC pós-reauth passou, e um MCP hospedado novo concluiu a
cadeia de autenticação e discovery. Nenhum material de credencial foi
registrado.

A primeira V5B de resolução de alvo foi bloqueada após 246 chamadas de
inventário e 24.500 itens, sem leitura de conteúdo. A V4 recusou repetir uma
varredura ampla. A recuperação rasa subsequente retornou 17 Shared Drives e
localizou o alvo após três primeiras páginas de Drive, com 1.079 itens; nenhum
conteúdo foi lido naquela etapa. A V5C executou uma única leitura real e
confirmou decisivamente `RESPONSE_VALIDATION / DOCS_STRUCTURAL_EXTRACTION /
PARAGRAPH_STRUCTURE / ELEMENT_STRUCTURE`, com zero chunks e sem continuação.

O plano de remediação V1 não atribuiu uma causa estática específica: há um só
boundary `ELEMENT_STRUCTURE`, mas ele contém seleção de union e diversos
validadores de payload. Por isso, esta entrega implementa somente um coletor
privado, context-local, desligado por padrão e first-failure-only. Ele conserva
apenas tipos fechados, presença de metadados reconhecidos, members de union de
allowlist, flag de desconhecido e label interno fechado de branch. Não grava
conteúdo, valores, chaves arbitrárias, URLs, pessoas, IDs, JSON bruto, logs,
arquivos ou campos MCP. O contrato público, catálogo, enums e códigos seguros
permanecem inalterados.

Os testes focados de parser, invariantes e protocolo registraram **338 passed**;
a regressão completa registrou **978 passed**, acima do baseline de 946, sem
Google, rede ou autenticação. O `server.py` não foi alterado nesta entrega e o
catálogo local permanece 24 tools: 20 Read, 4 Content, 0 Write, sem duplicatas.

```text
1.5.4 GOOGLE DOCS
│
├── ParagraphFailureKind                         ✅ COMPLETE — 946-pass local review
├── auth recovery                                ✅ COMPLETE — fresh hosted MCP healthy
├── target recovery                              ✅ COMPLETE — shallow 3-Drive recovery
├── real V5C ELEMENT_STRUCTURE                   ✅ COMPLETE — decisive real fingerprint
├── targeted diagnostic substrate                ✅ COMPLETE — private/local only
├── targeted real diagnostic                     ✅ COMPLETE — TEXT_RUN_CONTENT_INVALID
├── content remediation PLAN V1                  ✅ COMPLETE — narrower observation required
├── private content-state diagnostic              ✅ COMPLETE — private/local only; 139 focused / 996 regression
├── real content-state diagnostic                 ⬜ PENDING — explicit authorization required
├── concrete remediation plan                     ⬜ PENDING
├── remediation implementation                    ⬜ PENDING
├── post-fix real validation                      ⬜ PENDING
├── final review                                  ⬜ PENDING
└── checkpoint                                   ⬜ PENDING
```

Esta entrega não realizou Google, Drive, Docs, ADC, IAM, DWD, OAuth, rede,
login, staging, commit, push ou checkpoint. 1.5.4 permanece **NOT COMPLETE**.
PHASE STATUS = **SYNCHRONIZED**.

### 1.5.4 GOOGLE DOCS CONTENT — TEXT RUN CONTENT STATE DIAGNOSTIC IMPLEMENTATION V1 — 20/09/2026

**COMPLETE / LOCAL VALIDATION / SEM GOOGLE.** A observação privada,
context-local e first-failure-only agora contém `content_state` exclusivamente
quando o parser alcança `TEXT_RUN_CONTENT_INVALID`. O campo fechado distingue
`ABSENT`, `NULL`, `STRING`, `BOOLEAN`, `INTEGER`, `FLOAT`, `MAPPING`, `LIST` e
`OTHER_SCALAR`, sem reter valor, tamanho, repr ou nome arbitrário de tipo. A
classificação usa presença explícita de chave para separar `ABSENT` de `NULL` e
testa `bool` antes de `int`.

O predicado produtivo `text_run.get("content")`, a aceitação de conteúdo, a
validação UTF-16, os outcomes, fingerprints e códigos seguros permanecem
inalterados. Strings válidas e a divergência de índice não recebem
`content_state`; o último continua no branch
`TEXT_RUN_INDEX_LENGTH_MISMATCH`. A observação não faz parte de tool, schema
MCP, resultado público, auditoria, log, arquivo ou persistência.

Os testes focados registraram **139 passed** e a regressão completa **996
passed**, sem falhas e acima do baseline de 978. O catálogo local continua
24/20/4/0 e `server.py` não foi alterado. Não houve Google, Drive, Docs, rede,
ADC, IAM, DWD, OAuth, login, staging, commit, push ou checkpoint.

```text
private content-state diagnostic implementation   ✅ COMPLETE — 139 focused / 996 regression
real content-state diagnostic                     ⬜ PENDING — explicit authorization required
concrete remediation plan                         ⬜ PENDING
remediation implementation                        ⬜ PENDING
post-fix real validation                          ⬜ PENDING
final review                                      ⬜ PENDING
checkpoint                                        ⬜ PENDING
```

PHASE STATUS = **SYNCHRONIZED**.

### 1.5.4 GOOGLE DOCS — TEXT RUN STRING FAILURE DIAGNOSTIC IMPLEMENTATION V1 — 20/09/2026

**COMPLETE / LOCAL VALIDATION / SEM GOOGLE.** A evidência real mais recente
continua sendo `failing_branch=TEXT_RUN_CONTENT_INVALID` e
`content_state=STRING`. O reassessment estático confirmou que U+E907 é aceito
(categoria `Co`), caracteres private-use são aceitos e divergência de span
UTF-16 permanece no branch independente `TEXT_RUN_INDEX_LENGTH_MISMATCH`. A
causa real ainda é desconhecida; os três predicados STRING restantes são
`MAXIMUM_EXCEEDED`, `UTF8_ENCODING_INVALID` e
`DISALLOWED_C0_OR_C1_CONTROL`.

A observação privada first-failure-only agora inclui `string_failure_reason`,
um `Literal` privado fechado. Os três motivos são capturados no exato ponto de
rejeição de `_text()` e somente para `content_state=STRING`. Estados não string
continuam sem motivo; mismatch de índices e strings válidas também não recebem
esse campo. Não foi acrescentado fallback `OTHER`, nem conteúdo, comprimento,
hash, code point, nome/categoria Unicode, posição ou mensagem de exceção. A
captura continua desligada quando não há coletor privado. Limite de tamanho,
UTF-8 estrito, política de controles, TAB/LF/CR permitidos, tratamento de
U+E907, semântica de outcomes e superfície MCP permanecem inalterados.

Os testes focados cobrem os três rejeitos reais, C0 e C1, strings válidas
(incluindo U+E907, private-use, format, noncharacter e Unicode suplementar),
placeholder U+E907, validação UTF-16, mismatch isolado, first-failure,
disabled-by-default, equivalência de resultado e leakage. Resultado local:
**156 testes focados** e **1013 testes na regressão completa**, sem falhas e
acima do baseline de 996. Catálogo: 24 tools (20 Read, 4 Content, 0 Write), sem
duplicatas; `server.py` não foi alterado por este gate.

```text
1.5.4 GOOGLE DOCS
│
├── ELEMENT_STRUCTURE real                         ✅ CONCLUÍDO
├── TEXT_RUN_CONTENT_INVALID real                  ✅ CONCLUÍDO
├── content_state = STRING real                    ✅ CONCLUÍDO
├── string validation reassessment                 ✅ CONCLUÍDO
├── private string_failure_reason diagnostic       ✅ CONCLUÍDO — 3 exact sites / 156 focused / 1013 regression
├── real string failure reason diagnostic         ⬜ PENDENTE — real cause remains unknown
├── concrete remediation plan                      ⬜ PENDENTE
├── remediation implementation                    ⬜ PENDENTE
├── post-fix real validation                      ⬜ PENDENTE
├── final review                                  ⬜ PENDENTE
└── checkpoint                                    ⬜ PENDENTE — NOT AUTHORIZED
```

Nenhuma chamada Google, Drive, Docs, Workspace MCP, rede ou autenticação foi
feita; login ADC adicional necessário = NÃO; `gcloud auth login` necessário =
NÃO. Staging, commit e push = zero. O próximo gate recomendado é
**GOOGLE_DOCS_TEXT_RUN_STRING_FAILURE_TARGETED_REAL_DIAGNOSTIC_V1**, limitado a
uma leitura real controlada e sem remediação. 1.5.4 permanece **NOT COMPLETE**.
PHASE STATUS = **SYNCHRONIZED**.

### 1.5.4 GOOGLE DOCS — CONTROL RANGE DIAGNOSTIC IMPLEMENTATION V1 — 20/09/2026

**COMPLETE / LOCAL VALIDATION / SEM GOOGLE.** A leitura real V1B estabeleceu
`TEXT_RUN_CONTENT_INVALID / content_state=STRING /
string_failure_reason=DISALLOWED_C0_OR_C1_CONTROL`. Para este alvo,
`MAXIMUM_EXCEEDED` e `UTF8_ENCODING_INVALID` estão eliminados; a faixa exata
do controle permanece desconhecida. O plano estático confirmou que o predicado
atual rejeita U+0000–U+0008, U+000B, U+000C, U+000E–U+001F, U+007F e
U+0080–U+009F, permitindo TAB, LF e CR. As regras documentadas de
`InsertTextRequest` descrevem sanitização de inserção, não a validade completa
das respostas de leitura. U+E907 continua sendo o contraexemplo documentado que
impede equiparar essas semânticas. Nenhuma faixa atualmente rejeitada foi
provada, apenas por evidência estática, como legítima em uma resposta
`TextRun`; por isso, nenhuma remediação estática foi justificada.

Esta implementação acrescenta à mesma observação privada um único campo
`control_range`, limitado a `C0_0000_0008`, `VT_000B`, `FF_000C`,
`C0_000E_001F`, `DEL_007F` ou `C1_0080_009F`. A classificação ocorre somente
depois que o predicado existente rejeita o primeiro controle, com o coletor
privado instalado e no contexto de `textRun.content`. Não há `OTHER`/`UNKNOWN`,
valor exato de caractere/code point, contagem, posição ou conteúdo retido. A
rejeição C0/C1, UTF-8 estrito, limite, TAB/LF/CR, U+E907, spans UTF-16,
proveniência, chunks, resultados e demais callers de `_text` permanecem
inalterados; sem coletor a observação não é capturada.

Os testes focados verificam todas as seis faixas, fronteiras adjacentes,
TAB/LF/CR, primeira rejeição, leakage, demais falhas string, mismatch UTF-16,
U+E907 e strings Unicode válidas. Resultado local: **183 testes focados** e
**1040 testes na regressão completa**, sem falhas e acima do baseline de 1013.
A validação final usou o comando local do runbook com cache desativado e não
teve warnings. Catálogo: 24 tools (20 Read, 4 Content, 0 Write), sem
duplicatas; nenhum campo/tool/esquema MCP foi adicionado, `server.py` não
recebeu mudanças deste gate e `mcp.run()` permanece no final absoluto.

```text
1.5.4 GOOGLE DOCS
│
├── ELEMENT_STRUCTURE real                         ✅ CONCLUÍDO
├── TEXT_RUN_CONTENT_INVALID real                  ✅ CONCLUÍDO
├── content_state = STRING real                    ✅ CONCLUÍDO
├── DISALLOWED_C0_OR_C1_CONTROL real               ✅ CONCLUÍDO
├── control remediation Plan V1                    ✅ CONCLUÍDO — sem reparo estático justificado
├── private control-range diagnostic               ✅ CONCLUÍDO — 6 faixas / 183 focados / 1040 regressão
├── real control-range diagnostic                  ⬜ PENDENTE — autorização explícita
├── concrete remediation/reassessment plan         ⬜ PENDENTE
├── remediation implementation                     ⬜ PENDENTE
├── post-fix real validation                       ⬜ PENDENTE
├── final review                                   ⬜ PENDENTE
└── checkpoint                                     ⬜ PENDENTE — NOT AUTHORIZED
```

Não houve chamadas Google, Drive, Docs, Workspace MCP, rede ou autenticação;
login ADC adicional necessário = NÃO; `gcloud auth login` necessário = NÃO.
As 27 alterações preexistentes foram preservadas; `server.py` não foi alterado
por este gate. Staging = vazio; commit e push = zero; checkpoint não
autorizado. O próximo gate recomendado, ainda não executado, é
**GOOGLE_DOCS_TEXT_RUN_CONTROL_RANGE_TARGETED_REAL_DIAGNOSTIC_V1**, com no
máximo uma leitura real controlada. A faixa real permanece desconhecida e
1.5.4 segue **NOT COMPLETE**. PHASE STATUS = **SYNCHRONIZED**.

### 1.5.4 GOOGLE DOCS — VT TARGETED IMPLEMENTATION V1 — 21/09/2026

**COMPLETE / LOCAL VALIDATION / SEM GOOGLE.** A evidência real anterior
confirmou `TEXT_RUN_CONTENT_INVALID / content_state=STRING /
DISALLOWED_C0_OR_C1_CONTROL / VT_000B`, com diagnóstico fechado e
`CHANGED_DURING_AUDIT=NO`. A reassessment concreta concluiu que o leitor pode
receber VT em `TextRun.content` e que a representação normalizada mais segura é
ASCII SPACE, preservando o separador sem transportar o controle ou inventar
uma quebra de linha.

A validação genérica `_text()` mantém rejeição estrita por padrão. Somente a
chamada do conteúdo de `TextRun` permite VT; o texto original passa pelos
checks existentes de tipo, limite e UTF-8 e pela comparação de span UTF-16
antes da transformação. Depois do span válido, cada VT é substituído
individualmente por SPACE, antes do tratamento existente de U+E907 e da
filtragem/criação da unidade. Repetições não são colapsadas. A substituição
preserva um code unit UTF-16 e um byte UTF-8 por ocorrência, mantendo os
offsets de provenance, orçamento em bytes e cortes determinísticos de chunks.
VT-only usa a filtragem whitespace existente e pode resultar em `EMPTY` sem
falha. TAB/LF/CR, os outros cinco grupos C0/C1 rejeitados, strict UTF-8, o
limite de 32 MiB e a semântica U+E907 permanecem inalterados.

Os campos privados `failing_branch`, `content_state`, `string_failure_reason`
e `control_range` foram mantidos para a futura validação real pós-fix; nenhum
diagnóstico novo, enum, erro, campo ou tool MCP foi adicionado. Testes
sintéticos cobrem VT-only e casos mistos/repetidos/limítrofes, span incorreto,
isolamento de `_text()` genérico, interação com U+E907, TAB/LF/CR, provenance,
chunking e continuação. Resultado local: **194 testes focados** e **1051 testes
na regressão completa**, sem falhas e acima do baseline de 1040. Catálogo:
24 tools (20 Read, 4 Content, 0 Write), sem duplicatas; `server.py` não foi
alterado por este gate e `mcp.run()` permanece no final absoluto.

```text
1.5.4 GOOGLE DOCS
│
├── ELEMENT_STRUCTURE real                         ✅ CONCLUÍDO
├── TEXT_RUN_CONTENT_INVALID real                  ✅ CONCLUÍDO
├── content_state = STRING real                    ✅ CONCLUÍDO
├── DISALLOWED_C0_OR_C1_CONTROL real               ✅ CONCLUÍDO
├── control_range = VT_000B real                   ✅ CONCLUÍDO — validação decisiva
├── VT concrete reassessment                      ✅ CONCLUÍDO — VT→ASCII SPACE
├── VT targeted implementation                    ✅ CONCLUÍDO — 194 focados / 1051 regressão
├── real post-fix validation                      ⬜ PENDENTE — autorização separada
├── diagnostic cleanup review                     ⬜ PENDENTE
├── final review                                  ⬜ PENDENTE
└── checkpoint                                    ⬜ PENDENTE — NOT AUTHORIZED
```

Não houve chamadas Google, Drive, Docs, Workspace MCP, rede ou autenticação;
GOOGLE_WORKSPACE_CONTENT_* e `GDOCS_DIAGNOSTIC_TARGET_FILE_ID` não foram
necessários; login ADC adicional necessário = NÃO; `gcloud auth login`
necessário = NÃO. As 27 alterações preexistentes foram preservadas e somente
quatro caminhos autorizados receberam alterações desta entrega. Staging =
vazio; commit e push = zero; checkpoint não autorizado. Próximo gate recomendado:
**GOOGLE_DOCS_TEXT_RUN_VT_TARGETED_REAL_VALIDATION_V1**, sem retry e com
exatamente uma leitura de conteúdo após autorização separada. 1.5.4 permanece
**NOT COMPLETE**. PHASE STATUS = **SYNCHRONIZED**.

### 1.5.4 GOOGLE DOCS — VT REAL VALIDATION V1B + CONTROL RANGE CLEANUP V1 — 21/09/2026

**IMPLEMENTAÇÃO FUNCIONAL COMPLETA / SEM CHECKPOINT.** A validação real
pós-fix V1B foi executada pelo operador uma vez, com `manual retries=0`. O
precondition de ADC pós-reauth estava **HEALTHY**; a resolução do alvo passou
e o leitor de conteúdo de produção foi invocado exatamente uma vez. O resultado foi `PROCESSED`, com
2 chunks, sem continuação e `CHANGED_DURING_AUDIT=NO`. O defeito anterior
`TEXT_RUN_CONTENT_INVALID / STRING / DISALLOWED_C0_OR_C1_CONTROL / VT_000B` não
se repetiu; o leitor avançou além dele, não houve falha mais profunda e a
validação real da correção VT foi **PASS**.

A limpeza removeu somente o classificador privado `control_range`, seus seis
labels fechados e o plumbing/testes exclusivos dessa distinção. Foram
preservados `failing_branch`, `content_state`, `string_failure_reason` e o
coletor privado, context-local, first-failure-only e disabled-by-default. A
política de controles e o parser de produção, incluindo VT permitido apenas
em `TextRun.content`, validação UTF-16 antes da transformação e VT→SPACE,
permaneceram inalterados. Nenhuma superfície MCP ou taxonomia pública mudou.

A suíte focada terminou com **190 passed** e a regressão completa com **1047
passed**, sem falhas. Em relação aos baselines 194/1051, foram removidos 4
casos incident-only redundantes, nenhum teste foi adicionado e a redução líquida
foi 4; a cobertura de rejeição dos controles e os testes permanentes de VT
foram mantidos. Catálogo: 24 tools (20 Read, 4 Content, 0 Write), sem
duplicatas; `server.py` não mudou neste gate e `mcp.run()` continua no final
absoluto.

Não houve chamadas Google/API/auth nesta implementação; a evidência real V1B
acima é o resultado sanitizado fornecido pelo operador. As 27 alterações
preexistentes foram preservadas. Staging = vazio; commit e push = zero;
checkpoint não autorizado. A implementação funcional de 1.5.4 está completa;
revisão final e checkpoint permanecem pendentes. PHASE STATUS = **SYNCHRONIZED**.

```text
1.5.4 GOOGLE DOCS
│
├── content reading architecture                   ✅ CONCLUÍDO
├── real defect localization                      ✅ CONCLUÍDO
├── VT_000B diagnosis                              ✅ CONCLUÍDO
├── VT → SPACE implementation                     ✅ CONCLUÍDO
├── real post-fix validation V1B                  ✅ CONCLUÍDO — PROCESSED / 2 chunks / sem continuação
├── private diagnostic cleanup                    ✅ CONCLUÍDO — removido control_range
├── documentation sync                            ✅ CONCLUÍDO
├── final review                                  ⬜ PENDENTE
└── checkpoint / commit                           ⬜ PENDENTE — NOT AUTHORIZED
```
