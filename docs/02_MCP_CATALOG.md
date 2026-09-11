# Catálogo MCP atual

O servidor se chama **Google Workspace Admin** e é iniciado por `stdio`. O
catálogo atual possui 14 ferramentas, todas de leitura. Cada camada de API obtém
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

Todos os clientes HTTP têm timeout de 30 segundos e propagam respostas HTTP não
2xx. A paginação **ainda não está consolidada**: as ferramentas existentes
passam `maxResults`, mas não percorrem `nextPageToken`. A tool
`workspace_buildings_list` e `workspace_calendar_resources_list` preservam o
token opaco da API como `next_page_token` e aceitam-no como `page_token`, sem
percorrer páginas automaticamente. A consolidação geral continua uma entrega
pendente da FASE 1.

Buildings pertence à coleção `resources.buildings` da Admin SDK Directory API.
Resources / Salas pertence à coleção irmã `resources.calendars`; Features será
uma futura coleção irmã `resources.features`. As três usam o mesmo scope
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

## Limites de exposição

As respostas do Directory não devem ser repassadas integralmente. Os
serializadores em `server.py` selecionam somente os campos administrativos úteis
para cada recurso. Ao incluir novo campo, justifique sua necessidade e avalie
se ele expõe identificadores pessoais, dados de dispositivo ou outra informação
sensível.
