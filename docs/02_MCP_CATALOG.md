# Catálogo MCP atual

O servidor se chama **Google Workspace Admin** e é iniciado por `stdio`. O
catálogo atual possui 22 ferramentas, todas de leitura: 20 Read históricas e 2
tools Content da vertical 1.5.1. Cada camada de API obtém um token para o scope
mínimo que ela declara e o servidor serializa uma seleção de campos antes de
devolver a resposta ao Codex.

## Fase 1.5 — Foundation Content e Shared Drive Discovery

A Foundation Content permanece interna como infraestrutura. A entrega 1.5.1
registra somente `workspace_drives_list` e `workspace_drive_get`; a ferramenta
`workspace_drive_files_list` continua **NOT IMPLEMENTED / NOT REGISTERED**.
O catálogo público agora possui exatamente 22 tools: Content = 2 e Write = 0.
Os contratos de operação, transporte, scopes read-only, subjects e limites
continuam não sendo helpers MCP.

A remediação da Foundation adiciona um broker de autorização local, registry
fechado de profiles provisionados, máscaras internas de campos, filtros
estruturados com `trashed=false` invariável, caps de paginação por operação e
transport sem exposição pública de `httpx.Response`. A Remediation V2 exige
handles emitidos por registry/resolver, contexto emitido pelo broker e
resultados tipados por operação; nenhum desses componentes é ferramenta MCP.
O catálogo permanece com 20 ferramentas; Content tools e Write tools
permanecem em zero.

A Remediation V3 supera o wiring V2: a única superfície operacional futura é
`ContentRuntime.execute(request tipado)`. Authorities são handles sem dados,
issuer-bound por membership em closure; registry, resolver, broker, contexto,
normalização e HTTP adapter ficam capturados pelo runtime. Não existe API
Content para request/JSON genérico, `httpx.Response`, client attach, método,
host, endpoint, fields, scope ou capability fornecidos pelo caller. Os três
contratos Drive permanecem apenas internos e retornam DTOs allowlistados; o
inventário rejeita também respostas com `trashed` ausente ou diferente de
`false`.

| Ferramenta | Módulo | Parâmetros e limites | Resultado resumido |
| --- | --- | --- | --- |
| `workspace_status` | `server.py` | nenhum | estado e arquitetura de autenticação |
| `workspace_users_list` | `directory/users.py` | `max_results` 1–100, padrão 5; `page_token` opcional não vazio | uma página de usuários ordenados por e-mail e `next_page_token` |
| `workspace_user_get` | `directory/users.py` | `user_key` não vazio | usuário por e-mail, alias ou ID |
| `workspace_groups_list` | `directory/groups.py` | `max_results` 1–200, padrão 20; `page_token` opcional não vazio | uma página de grupos do customer atual e `next_page_token` |
| `workspace_group_members_list` | `directory/group_members.py` | `group_key`; `max_results` 1–200; `page_token` opcional não vazio | uma página de membros diretos e `next_page_token` |
| `workspace_orgunits_list` | `directory/orgunits.py` | caminho com `/`; tipo válido | unidades organizacionais |
| `workspace_mobile_devices_list` | `directory/mobile_devices.py` | `max_results` 1–100, padrão 100; `page_token` opcional não vazio | uma página de dispositivos móveis, projeção FULL e `next_page_token` |
| `workspace_chromeos_devices_list` | `directory/chromeos_devices.py` | `max_results` 1–300, padrão 100; `page_token` opcional não vazio | uma página de dispositivos ChromeOS, projeção FULL e `next_page_token` |
| `workspace_roles_list` | `directory/roles.py` | `max_results` 1–100, padrão 100; `page_token` opcional não vazio | uma página de funções administrativas e `next_page_token` |
| `workspace_role_assignments_list` | `directory/role_assignments.py` | `max_results` 1–100, padrão 100; `page_token` opcional não vazio | uma página de atribuições e `next_page_token` |
| `workspace_domains_list` | `directory/domains.py` | nenhum | domínios do customer atual |
| `workspace_domain_aliases_list` | `directory/domain_aliases.py` | `parent_domain_name` opcional | aliases de domínio |
| `workspace_buildings_list` | `directory/resources/buildings.py` | `max_results` 1–500, padrão 100; `page_token` opcional não vazio | edifícios serializados e `next_page_token` da página |
| `workspace_calendar_resources_list` | `directory/resources/calendars.py` | `max_results` 1–500, padrão 100; `page_token`, `order_by` e `query` opcionais não vazios | recursos corporativos serializados e `next_page_token` da página |
| `workspace_calendar_features_list` | `directory/resources/features.py` | `max_results` 1–500, padrão 100; `page_token` opcional não vazio | features serializadas e `next_page_token` da página |
| `workspace_admin_audit_list` | `reports/admin_audit.py` | `max_results` 1–100, padrão 25; `page_token`, `event_name`, `filters`, `start_time`, `end_time`, `actor_ip_address` e `org_unit_id` opcionais não vazios; `user_key` padrão `all` | atividades Admin Audit serializadas e `next_page_token` da página |
| `workspace_login_audit_list` | `reports/login_audit.py` | `max_results` 1–100, padrão 25; `page_token`, `event_name`, `filters`, `start_time`, `end_time`, `actor_ip_address` e `org_unit_id` opcionais não vazios; `user_key` padrão `all` | atividades Login Audit serializadas conservadoramente e `next_page_token` da página |
| `workspace_drive_audit_list` | `reports/drive_audit.py` | `max_results` 1–100, padrão 25; `page_token`, `event_name`, `filters`, `start_time`, `end_time`, `actor_ip_address` e `org_unit_id` opcionais não vazios; `user_key` padrão `all` | atividades Drive Audit serializadas conservadoramente e `next_page_token` da página |
| `workspace_user_usage_get` | `reports/user_usage.py` | `date` obrigatório YYYY-MM-DD válido; `max_results` 1–100, padrão 25; `page_token`, `parameters`, `filters` e `org_unit_id` opcionais não vazios; `user_key` padrão `all` | User Usage Reports implementados e validados, serializer allowlisted, warnings sanitizados e `next_page_token` da página |
| `workspace_customer_usage_get` | `reports/customer_usage.py` | `date` obrigatório YYYY-MM-DD válido; `parameters` obrigatório com CSV de métricas allowlisted; `page_token` opcional | Customer Usage Reports implementados, serializer integer allowlisted, warnings sanitizados e `next_page_token` da página |
| `workspace_drives_list` | `content` / `server.py` | `page_size` StrictInt 1–100, padrão 25; `page_token` StrictStr opcional não vazio; `max_items` StrictInt 1–100, padrão 100; `use_domain_admin_access` StrictBool, padrão `false`; uma página, sem auto-pagination | Shared Drives allowlisted como `{drive_id, name}` e token Google validado |
| `workspace_drive_get` | `content` / `server.py` | `drive_id` StrictStr, trim boundary, 1–256 caracteres, sem whitespace/control; `use_domain_admin_access` StrictBool, padrão `false` | um Shared Drive allowlisted como `{drive_id, name}` |

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
| User Usage | `/admin/reports/v1/usage/users/{userKey}/dates/{date}` |
| Customer Usage | `/admin/reports/v1/usage/dates/{date}` |
| Shared Drive Discovery — list | `https://www.googleapis.com/drive/v3/drives` |
| Shared Drive Discovery — get | `https://www.googleapis.com/drive/v3/drives/{driveId}` |

Todos os clientes HTTP têm timeout de 30 segundos, não fazem retry e convertem
falhas HTTP/transportes dos módulos Directory consolidados em erros seguros,
sem body ou headers. As ferramentas list pagináveis passam `max_results` como
`maxResults`, `page_token` como `pageToken` e processam exatamente uma página;
`nextPageToken` é devolvido como `next_page_token`. Não há auto-pagination.
`page_token` deve ser `None` ou uma string não vazia; valores vazios e tipos
arbitrários são rejeitados. `max_results` rejeita bool, float, string numérica,
zero e valores acima do limite específico do endpoint.

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
checkpoint Git está concluído.

## Limites de exposição

As respostas do Directory não devem ser repassadas integralmente. Os
serializadores em `server.py` selecionam somente os campos administrativos úteis
para cada recurso. Ao incluir novo campo, justifique sua necessidade e avalie
se ele expõe identificadores pessoais, dados de dispositivo ou outra informação
sensível.

Os serializers de Mobile e ChromeOS preservam deliberadamente `device_id`,
serial, IMEI/MEID, MAC, `annotated_user` e `annotated_location` quando
fornecidos pela API, porque são necessários ao inventário administrativo. A
exposição é intencional e deve ser tratada como potencialmente sensível pelo
consumidor. Admin Audit mantém o contrato de parâmetros já validado; seus
valores podem ser dados administrativos potencialmente sensíveis.

Para a migração de menor privilégio, o CODE TARGET e a DWD atual são `users` →
`admin.directory.user.readonly`, `groups` →
`admin.directory.group.readonly`, `group members` →
`admin.directory.group.member.readonly` e `orgunits` →
`admin.directory.orgunit.readonly`. A migração manual foi confirmada pelo
usuário e as quatro validações reais readonly foram concluídas com sucesso.
Os scopes amplos anteriores permanecem somente no histórico.

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

`workspace_drive_audit_list` é a 18ª tool local e consulta somente
`/admin/reports/v1/activity/users/{userKey}/applications/drive` da Reports API,
com `applicationName=drive` fixo. Sua assinatura é:

```text
workspace_drive_audit_list(
    max_results=25,
    page_token=None,
    user_key="all",
    event_name=None,
    filters=None,
    start_time=None,
    end_time=None,
    actor_ip_address=None,
    org_unit_id=None,
)
```

`max_results` é limitado a 1–100, padrão 25. Os parâmetros opcionais não
podem ser vazios ou conter somente whitespace; datas devem estar em RFC3339 e,
quando ambas presentes, `start_time` deve anteceder `end_time`. A tool passa
somente `maxResults`, `pageToken`, `eventName`, `filters`, `startTime`,
`endTime`, `actorIpAddress` e `orgUnitID`. Não envia `customerId`, filtros
recentes de recurso/rede/status/aplicação/agente/dispositivo nem
`includeSensitiveData`, não interpreta integralmente a gramática de `filters`,
não percorre páginas e não cria retries.

O retorno é uma única página em `{"activities": [...],
"next_page_token": ...}`. O serializer de Drive é independente do serializer
de Admin Audit e usa allowlist: expõe timestamp/qualificador, tipo/nome do
evento, `primary_event`, categorias operacionais allowlisted, ator/IP
normalizados e IDs de arquivo/Shared Drive como identificadores opacos. Mantém
somente o nome de parâmetros potencialmente sensíveis como `doc_title`,
`owner`, `target_user`, `target_domain`, queries, URLs, labels e valores de
conteúdo. Omite estruturas desconhecidas, `sensitiveParameters`,
`resourceIds`, `resourceDetails`, `networkInfo`, `userDeviceInfo`, OAuth,
agentic metadata, `kind`, `etag`, `ownerDomain` e payload bruto.

O catálogo esperado após esta implementação é de 18 tools. Em 11/09/2026, a
REAL VALIDATION do Drive Audit foi concluída exclusivamente pelo MCP original
carregado pelo host, com exatamente uma chamada
`workspace_drive_audit_list(max_results=1)`: sucesso, 1 Activity e
`next_page_token` presente. A cadeia keyless foi validada até a Reports API;
nenhum conteúdo real de Activity foi persistido. O checkpoint Git desta entrega
é concluído com o commit autorizado após as verificações finais.

`workspace_user_usage_get` é a 19ª tool local e usa somente o método
`userUsageReport.get` da Reports API. A assinatura é:

```text
workspace_user_usage_get(
    date,
    max_results=25,
    page_token=None,
    user_key="all",
    parameters=None,
    filters=None,
    org_unit_id=None,
)
```

Ela usa `UserUsageReport.get` da Reports API, processa uma página por chamada,
não cria retry automático e limita `max_results` a 1–100. O serializer é
allowlisted e reduz warnings a indicadores agregados.

`date` deve ser estritamente `YYYY-MM-DD` e representar uma data válida. A
tool encaminha somente `maxResults`, `pageToken`, `parameters`, `filters` e
`orgUnitID`; não envia `customerId`, não usa `activities.list`, Drive Activity
API ou `customerUsageReports`, não percorre páginas e não cria retries.

O retorno preserva, para cada relatório, somente `date`, `profile_id` derivado
de `entity.profileId` e parâmetros allowlisted. `userEmail`, `entityId`,
`customerId`, `kind`, `etag`, estruturas desconhecidas, `stringValue` genérico,
`msgValue` e o payload bruto são omitidos. Timestamps de Accounts só aparecem
quando foram explicitamente solicitados, usando `timestamp_last_login` como o
nome atual. Warnings são reduzidos a `warnings_present` e `warnings_count`.

O catálogo local confirmado após o IMPLEMENT de User Usage era de 19 tools
antes da inclusão de Customer Usage. A implementação e os testes locais usam
mocks. A REAL VALIDATION foi executada em `2026-09-12`
pelo MCP original com uma única chamada para a data do relatório solicitado
`date=2026-09-10`,
`max_results=1`, `parameters=accounts:used_quota_in_percentage` e
`user_key=all`: sucesso, `usageReports=1`, `next_page_token` presente,
`warnings_present=true` e `warnings_count=1`, sem retry ou paginação adicional.
A resposta final permanece allowlisted e não inclui campos diagnósticos
temporários no contrato. DWD, scopes e demais configurações administrativas não
foram alterados.

`workspace_customer_usage_get` é a 20ª tool local e usa somente
`CustomerUsageReports.get` da Reports API. A assinatura é:

```text
workspace_customer_usage_get(
    date,
    parameters,
    page_token=None,
)
```

`date` é obrigatório, estritamente `YYYY-MM-DD` e representa exclusivamente a
data solicitada do relatório. `parameters` é obrigatório e deve ser um CSV de
métricas totalmente qualificadas, sem wildcard, aplicação inteira, métrica
desconhecida ou duplicata. Espaços externos de cada item são removidos; a
ordem solicitada é preservada no CSV encaminhado.

A allowlist inicial contém somente estas dez métricas integer:
`accounts:num_users`, `accounts:num_archived_users`,
`accounts:num_disabled_accounts`, `accounts:num_suspended_users`,
`accounts:customer_used_quota_in_mb`, `accounts:drive_used_quota_in_mb`,
`accounts:gmail_used_quota_in_mb`, `accounts:team_drive_used_quota_in_mb`,
`accounts:total_quota_in_mb` e `accounts:used_quota_in_mb`. As demais
aplicações e métricas deprecated/legacy ficam omitidas nesta versão.

`page_token` é encaminhado como `pageToken`; a resposta normaliza
`nextPageToken` para `next_page_token`. Cada invocation processa uma única
página, sem retry automático e com timeout de 30 segundos. `customerId`,
`maxResults`, `userKey`, `filters` e `orgUnitID` não fazem parte do contrato.

O serializer preserva somente `date` e métricas integer solicitadas e
allowlisted. Omite entity, identificadores, `kind`, `etag`, `stringValue`,
`datetimeValue`, `msgValue`, `boolValue`, warnings brutos e o payload bruto.
Warnings, quando presentes, são reduzidos a `warnings_present` e
`warnings_count`. A REAL VALIDATION V9 foi concluída anteriormente com uma
única chamada autorizada; os testes desta IMPLEMENT usam mocks e não executam
nova chamada Google.

## Fase 1.5 — Foundation Remediation Implement V4

A Foundation V4 continua sem tools públicas Content. A única fachada local
suportada é `ContentRuntime.execute(request tipado)` e `ContentRuntime.close()`;
nenhum request pode fornecer executor, client, adapter, broker, resolver,
authority, host, endpoint, método, scope ou fields.

Os contratos internos `drive.list`, `drive.get` e `drive.files.list` derivam
host, path, método GET, fields, filtros, invariantes e parser de uma identidade
fechada de operação. Resultados continuam DTOs allowlistados e
`drive.files.list` exige `trashed is False` estrito. Policies de paginação,
contexto e retry são verificadas novamente no ponto de consumo; subclasses e
objetos duck-typed de segurança falham fechado.

No snapshot histórico da Foundation V4, o catálogo permanecia com exatamente 20
tools, Content tools = 0 e Write tools = 0; essa fotografia é preservada para
o histórico. O estado corrente após a entrega 1.5.1 está definido abaixo.

## Fase 1.5.1 — Shared Drive Discovery — IMPLEMENT V1

As duas tools públicas usam a identidade Content configurada internamente e
não expõem `profile_id`, subject, credentials, access token, endpoint, método,
scope, fields ou query livre. O runtime é criado somente na primeira invocação
funcional; importar o módulo e enumerar `tools/list` não executa autenticação.
Sem Content provisioning, a invocação retorna um erro seguro antes do HTTP.

`workspace_drives_list` tem a assinatura lógica:

```text
workspace_drives_list(
    page_size=25,
    page_token=None,
    max_items=100,
    use_domain_admin_access=False,
)
```

`page_size` e `max_items` são inteiros estritos entre 1 e 100. O adapter envia
`pageSize=min(page_size, max_items)`; não inventa token local e não percorre
mais de uma página. `page_token` é uma string opaca não vazia ou `None`. O
request interno é `drive.list`, e o retorno público é somente:

```json
{"drives": [{"drive_id": "...", "name": "..."}], "next_page_token": null}
```

`workspace_drive_get` aceita somente `drive_id` como identificador operacional
opaco, com trim nas bordas, 1–256 caracteres, sem whitespace ou caracteres de
controle; o case é preservado. O ID inteiro é codificado como um único path
segment antes de `GET`. O retorno público é somente:

```json
{"drive": {"drive_id": "...", "name": "..."}}
```

Nomes duplicados são preservados. Nome não é chave operacional e nenhum lookup,
fuzzy match ou desambiguação silenciosa por nome existe nesta versão.

O modo administrativo encaminha `useDomainAdminAccess=true` somente depois do
profile Content aprovado, subject validado, capability `DRIVE`, capability
administrativa `SHARED_DRIVE_DISCOVERY` e compatibilidade da operação. O
padrão é `false`; a flag não é bypass de autorização nem universaliza acesso a
conteúdo.

O adapter fixa HTTPS, host `www.googleapis.com`, método GET e fields
`nextPageToken,drives(id,name)` / `id,name`. Redirects ficam desabilitados,
timeout é controlado e a política padrão faz uma tentativa, com máximo interno
de três para casos explicitamente retryable. 400/401/403/404 nunca são repetidos.
O header Authorization é produzido internamente pelo provider keyless e nunca
entra no request MCP, DTO, audit, erro ou representação pública.

`workspace_drive_files_list` continua ausente: os contratos internos da
Foundation são preservados para 1.5.2, mas não são ferramenta desta entrega.
