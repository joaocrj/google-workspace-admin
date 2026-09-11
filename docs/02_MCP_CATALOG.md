# Catálogo MCP atual

O servidor se chama **Google Workspace Admin** e é iniciado por `stdio`. O
catálogo atual possui 12 ferramentas, todas de leitura. Cada camada de API obtém
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

Todos os clientes HTTP têm timeout de 30 segundos e propagam respostas HTTP não
2xx. A paginação **ainda não está consolidada**: as ferramentas passam
`maxResults`, mas não percorrem `nextPageToken`. Essa é uma entrega pendente da
FASE 1, não uma garantia de inventário completo.

## Limites de exposição

As respostas do Directory não devem ser repassadas integralmente. Os
serializadores em `server.py` selecionam somente os campos administrativos úteis
para cada recurso. Ao incluir novo campo, justifique sua necessidade e avalie
se ele expõe identificadores pessoais, dados de dispositivo ou outra informação
sensível.
