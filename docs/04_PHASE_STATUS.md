# Andamento das fases

Última consolidação documental: **13/09/2026 — READ LAYER CONSOLIDATION CHECKPOINT / COMMIT V1 / COMPLETE**. Esta árvore é a fonte
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

**Ponteiro atual: STOP — READ LAYER CONSOLIDATION COMPLETE; próxima fase não iniciada.** O FINAL REVIEW V1 ficou
preservado como histórico bloqueado pelos achados FR-01 a FR-04, apesar de
**411 testes aprovados** naquele momento. O FINAL REVIEW V2 confirmou os quatro
achados corrigidos/verificados, **459 testes aprovados**, catálogo com 20 tools,
diff limpo e ausência de chamadas Google. O CHECKPOINT / COMMIT V1 é registrado
neste commit; nenhuma próxima fase foi iniciada.
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
