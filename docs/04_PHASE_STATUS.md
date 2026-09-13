# Andamento das fases

Última consolidação documental: **12/09/2026**. Esta árvore é a fonte
persistente do roadmap/status e combina o estado do código em `master`, os
commits e o inventário de validações fornecido pelo usuário. Atualize-a no
mesmo change set de qualquer avanço. Evidência de produção deve registrar
somente status e contagens seguras.

## Convenção de estados e evidências

Os estados formais de entregas são `✅ CONCLUÍDO`, `← EM ANDAMENTO`,
`⬜ PENDENTE` e `⛔ BLOQUEADO`. Resultados como HTTP 200, contagens, hashes de
commit, VALIDADO, VERIFICADA e ADICIONADO são evidências, não estados
concorrentes; preserve-os como detalhes da entrega.

## ROADMAP SYNCHRONIZATION RULE

Sempre que uma entrega alterar o estado de uma fase, feature ou subetapa, este
arquivo deve ser atualizado no mesmo conjunto de mudanças.

Isso inclui, quando aplicável: `PLAN → IMPLEMENT → REAL VALIDATION →
REVIEW/CHECKPOINT → COMMIT`.

Nenhuma feature será considerada documentalmente concluída enquanto sua
posição/status correspondente não estiver refletida nesta árvore.

**Ponteiro atual: FASE 1 → 4. Consolidação da camada Read.** Source Discovery
DIAG V1 foi concluído com classificação H6; o Host Remediation FINAL PLAN V2
também foi concluído. O R2 Manual Lifecycle foi concluído com SUCCESS na
validação do catálogo do host original. A REAL GOOGLE CALL V9, a FINAL REVIEW e
o CHECKPOINT / COMMIT foram concluídos com sucesso.

A paginação com `nextPageToken` permanece planejada para a etapa de
**Consolidação da camada Read** e não substitui a próxima entrega prioritária.
Buildings preserva o token por página, sem antecipar essa consolidação global.

```text
FASE 1 — READ / ADMIN INVENTORY
│
├── 1. Directory — identidade e estrutura                 ✅ CONCLUÍDO
│   ├── Users                                              ✅ CONCLUÍDO
│   │   ├── API Directory                                   ✅ CONCLUÍDO
│   │   ├── endpoint `/admin/directory/v1/users`            ✅ CONCLUÍDO
│   │   ├── scope `admin.directory.user`                    ✅ CONCLUÍDO
│   │   ├── módulo `directory/users.py`                     ✅ CONCLUÍDO
│   │   ├── workspace_users_list                            ✅ CONCLUÍDO
│   │   └── workspace_user_get                              ✅ CONCLUÍDO
│   ├── Groups                                             ✅ CONCLUÍDO
│   │   ├── endpoint `/admin/directory/v1/groups`           ✅ CONCLUÍDO
│   │   ├── scope `admin.directory.group`                   ✅ CONCLUÍDO
│   │   ├── módulo `directory/groups.py`                    ✅ CONCLUÍDO
│   │   └── workspace_groups_list                           ✅ CONCLUÍDO
│   ├── Group Members                                      ✅ CONCLUÍDO
│   │   ├── endpoint `/admin/directory/v1/groups/{groupKey}/members` ✅ CONCLUÍDO
│   │   ├── scope `admin.directory.group.member`            ✅ CONCLUÍDO
│   │   ├── módulo `directory/group_members.py`             ✅ CONCLUÍDO
│   │   └── workspace_group_members_list                    ✅ CONCLUÍDO
│   ├── Organizational Units — Read                        ✅ CONCLUÍDO
│   │   ├── endpoint `/admin/directory/v1/customer/my_customer/orgunits` ✅ CONCLUÍDO
│   │   ├── scope `admin.directory.orgunit`                 ✅ CONCLUÍDO
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
├── 3. Reports / Auditoria                                 ← EM ANDAMENTO
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
│       ├── REAL VALIDATION V1                                  ⛔ HOST 19
│       │   ├── host catalog                                    ⚠️ 19
│       │   ├── `workspace_customer_usage_get`                    ❌ AUSENTE
│       │   └── Google call                                      ⏭️ NÃO EXECUTADA
│       ├── REAL VALIDATION V2                                  ✅ DIAGNÓSTICO
│       │   └── restart externo                                  ⚠️ NECESSÁRIO
│       ├── REAL VALIDATION V3                                  ⛔ HOST 19 PÓS-RESTART
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
└── 4. Consolidação da camada Read                         ⬜ PENDENTE
    ├── paginação com nextPageToken                        ⬜ PENDENTE
    ├── tratamento uniforme de erros                       ⬜ PENDENTE
    ├── revisão de scopes mínimos                          ⬜ PENDENTE
    ├── serialização consistente                           ⬜ PENDENTE
    ├── consistência do catálogo MCP                       ⬜ PENDENTE
    ├── documentação final                                 ⬜ PENDENTE
    └── inventário/testes finais                           ⬜ PENDENTE

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

Ao executar a suíte novamente, acrescente uma evidência com data e contagem
atuais; não apague o contexto histórico sem uma razão.
