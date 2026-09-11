# Catálogo MCP atual

O servidor se chama **Google Workspace Admin** e é iniciado por `stdio`. O
catálogo atual possui 17 ferramentas, todas de leitura. Cada camada de API obtém
um token para o scope mínimo que ela declara e o servidor serializa uma seleção
de campos antes de devolver a resposta ao Codex.

| Ferramenta | Módulo | Parâmetros e limites | Resultado resumido |
| --- | --- | --- | --- |
| `workspace_status` | `server.py` | nenhum | estado e arquitetura de autenticação |
| `workspace_users_list` | `directory/users.py` | `max_results` 1–100, padrão 5 | usuários ordenados por e-mail |
| `workspace_user_get` | `directory/users.py` | `user_key` não vazio | usuário por e-mail, alias ou ID |
| `workspace_groups_list` | `directory/groups.py` | `max_results` 1–200, padrão 20 | grupos do customer atual |
| `workspace_group_members_list` | `directory/group_members.py` | `group_key`; `max_results` 1–200 | membros diretos do grupo |
| `workspace_orgunits_list` | `directory/orgunits.py` | caminho com `/`; tipo válido | unidades organizacionais |
| `workspace_mobile_devices_list` | `directory/mobile_devices.py` | `max_results` 1–100, padrão 100 | dispositivos móveis, projeção FULL |
| `workspace_chromeos_devices_list` | `directory/chromeos_devices.py` | `max_results` 1–300, padrão 100 | dispositivos ChromeOS, projeção FULL |
| `workspace_roles_list` | `directory/roles.py` | `max_results` 1–100, padrão 100 | funções administrativas |
| `workspace_role_assignments_list` | `directory/role_assignments.py` | `max_results` 1–100, padrão 100 | atribuições de função |
| `workspace_domains_list` | `directory/domains.py` | nenhum | domínios do customer atual |
| `workspace_domain_aliases_list` | `directory/domain_aliases.py` | `parent_domain_name` opcional | aliases de domínio |
| `workspace_buildings_list` | `directory/resources/buildings.py` | `max_results` 1–500, padrão 100; `page_token` opcional não vazio | edifícios serializados e `next_page_token` da página |
| `workspace_calendar_resources_list` | `directory/resources/calendars.py` | `max_results` 1–500, padrão 100; `page_token`, `order_by` e `query` opcionais não vazios | recursos corporativos serializados e `next_page_token` da página |
| `workspace_calendar_features_list` | `directory/resources/features.py` | `max_results` 1–500, padrão 100; `page_token` opcional não vazio | features serializadas e `next_page_token` da página |
| `workspace_admin_audit_list` | `reports/admin_audit.py` | `max_results` 1–100, padrão 25; `page_token`, `event_name`, `filters`, `start_time`, `end_time`, `actor_ip_address` e `org_unit_id` opcionais não vazios; `user_key` padrão `all` | atividades Admin Audit serializadas e `next_page_token` da página |
| `workspace_login_audit_list` | `reports/login_audit.py` | `max_results` 1–100, padrão 25; `page_token`, `event_name`, `filters`, `start_time`, `end_time`, `actor_ip_address` e `org_unit_id` opcionais não vazios; `user_key` padrão `all` | atividades Login Audit serializadas conservadoramente e `next_page_token` da página |

## Endpoints Directory em uso

| Capacidade | Endpoint REST |
| --- | --- |
| Usuários | `/admin/directory/v1/users` e `/users/{userKey}` |
| Grupos e membros | `/admin/directory/v1/groups` e `/groups/{groupKey}/members` |
| OUs | `/admin/directory/v1/customer/my_customer/orgunits` |
| Mobile | `/admin/directory/v1/customer/my_customer/devices/mobile` |
| ChromeOS | `/admin/directory/v1/customer/my_customer/devices/chromeos` |
| Funções | `/admin/directory/v1/customer/my_customer/roles` |
| Atribuições | `/admin/directory/v1/customer/my_customer/roleassignments` |
| Domínios | `/admin/directory/v1/customer/my_customer/domains` |
| Aliases | `/admin/directory/v1/customer/my_customer/domainaliases` |
| Buildings | `/admin/directory/v1/customer/my_customer/resources/buildings` |
| Resources / Salas | `/admin/directory/v1/customer/my_customer/resources/calendars` |
| Features | `/admin/directory/v1/customer/my_customer/resources/features` |

## Endpoint Reports em uso

| Capacidade | Endpoint REST |
| --- | --- |
| Admin Audit | `/admin/reports/v1/activity/users/{userKey}/applications/admin` |
| Login Audit | `/admin/reports/v1/activity/users/{userKey}/applications/login` |

Todos os clientes HTTP têm timeout de 30 segundos e propagam respostas HTTP não
2xx. A paginação **ainda não está consolidada**: as ferramentas existentes
passam `maxResults`, mas não percorrem `nextPageToken`. A tool
`workspace_buildings_list` e `workspace_calendar_resources_list` preservam o
token opaco da API como `next_page_token` e aceitam-no como `page_token`, sem
percorrer páginas automaticamente. A consolidação geral continua uma entrega
pendente da FASE 1.

Buildings pertence à coleção `resources.buildings` da Admin SDK Directory API.
Resources / Salas pertence à coleção irmã `resources.calendars`; Features
pertence à coleção irmã `resources.features`. As três usam o mesmo scope
`admin.directory.resource.calendar.readonly`, mas endpoints distintos.

Em Resources / Salas, `order_by` e `query` são passados para os parâmetros
oficiais `orderBy` e `query` da Directory API após rejeitar valores vazios. A
implementação não interpreta a gramática desses filtros nem adiciona retries ou
percurso automático de páginas.

Em 11/09/2026, após reautenticação manual da ADC pelo usuário, um processo MCP
`stdio` novo redescobriu as 13 ferramentas, incluindo
`workspace_buildings_list`, sem expor os serializadores. A invocação real
autorizada retornou zero Buildings, sem página seguinte. Nenhum dado de
Building nem token de paginação foi registrado.

O catálogo local inclui a 14ª tool,
`workspace_calendar_resources_list`; os testes de protocolo confirmam que ela
está registrada e que seus helpers/serializers não integram o catálogo MCP.
Em 11/09/2026, um processo MCP `stdio` novo redescobriu as 14 ferramentas,
incluindo Buildings e Resources / Salas, sem helpers/serializers expostos. A
única invocação real de Resources / Salas, limitada a `max_results=1`, foi
bem-sucedida com zero recursos e sem página seguinte. Nenhum dado de recurso
ou token de paginação foi registrado.

O catálogo local agora inclui a 15ª tool,
`workspace_calendar_features_list`. Ela envia somente `maxResults` e, quando
informado, `pageToken`, pois `resources.features.list` não documenta ordenação
nem filtro. A implementação preserva `nextPageToken` como
`next_page_token`, não percorre páginas e não cria retries. Em 11/09/2026, um
processo MCP `stdio` novo redescobriu as 15 tools, incluindo Buildings,
Resources / Salas e Features, sem helpers/serializers expostos. A única
invocação real de Features, limitada a `max_results=1`, foi bem-sucedida com
zero Features e sem página seguinte. Nenhum dado de Feature, token de página
ou material de autenticação foi registrado.

Com o checkpoint de Features, as três coleções de recursos corporativos de
Calendar — Buildings, Resources / Salas e Features — estão implementadas,
testadas e validadas no MCP real.

`workspace_admin_audit_list` é a 16ª tool local. Ela usa o caminho Reports API
com `applicationName=admin` fixo e não expõe `customerId`, a aplicação nem o
sujeito DWD. Encaminha apenas os filtros explicitamente suportados por seu
contrato, preserva `nextPageToken` como `next_page_token` e não percorre páginas
ou cria retries. A API aceita até 1000 registros por página, mas o MCP restringe
deliberadamente cada consulta a 1–100, com padrão 25. Datas devem estar em RFC
3339 e, quando ambas existem, `start_time` deve anteceder `end_time`.

As respostas de Admin Audit omitem estruturalmente `kind`, `etag`,
`ownerDomain`, identificadores de perfil/chave/OAuth do ator,
`sensitiveParameters`, `resourceIds`, `networkInfo`, `resourceDetails` e
payload bruto. Parâmetros comuns são normalizados, inclusive seus valores
aninhados não sensíveis. A tool não envia `includeSensitiveData`.

A DWD para `admin.reports.audit.readonly` foi confirmada manualmente pelo
usuário, assim como o sujeito delegado Superadministrador. O launcher atual do
processo MCP usa diretamente o Python da `.venv`. A REAL VALIDATION foi
executada exatamente uma vez por MCP e retornou 1 Activity com
`next_page_token` presente; nenhum conteúdo da Activity foi registrado. O
checkpoint Git permanece pendente.

## Limites de exposição

As respostas do Directory não devem ser repassadas integralmente. Os
serializadores em `server.py` selecionam somente os campos administrativos úteis
para cada recurso. Ao incluir novo campo, justifique sua necessidade e avalie
se ele expõe identificadores pessoais, dados de dispositivo ou outra informação
sensível.

`workspace_login_audit_list` é a 17ª tool local. Ela fixa
`applicationName=login`, usa exclusivamente o scope
`https://www.googleapis.com/auth/admin.reports.audit.readonly` e aceita apenas
os parâmetros de investigação previstos pelo contrato: `user_key`,
`max_results`, `page_token`, `event_name`, `filters`, `start_time`, `end_time`,
`actor_ip_address` e `org_unit_id`. O MCP restringe cada página a 1–100
registros, padrão 25, preserva `nextPageToken` como `next_page_token`, não
percorre páginas e não cria retries. Não envia `customerId`,
`includeSensitiveData` nem filtros de recursos, dispositivos, rede, agentes,
OAuth ou status.

O serializer de Login Audit expõe somente timestamp/qualificador, ator, IP,
tipo/nome do evento e valores allowlisted de `login_type`,
`login_challenge_method`, `login_challenge_status`, `is_suspicious` e
`is_second_factor`. Valores de e-mail afetado, timestamps internos,
`sensitive_action_name`, `login_failure_type`, `sensitiveParameters`,
`resourceIds`, status bruto, metadados e payload bruto são omitidos
estruturalmente. A implementação local está concluída. Em 11/09/2026, a REAL
VALIDATION MCP foi concluída em uma única chamada
`workspace_login_audit_list(max_results=1)`, retornando 1 Activity e
`next_page_token` presente; nenhum conteúdo de Activity foi registrado. O
checkpoint Git é concluído nesta entrega.
