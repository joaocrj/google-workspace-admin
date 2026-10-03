# Runbook de operação e desenvolvimento

## Pré-requisitos locais

- Windows e PowerShell, com `uv` disponível;
- Python compatível com `>=3.11`;
- ADC local válida para a identidade autorizada a usar `signJwt`;
- acesso ao Google Workspace somente pela arquitetura DWD documentada.

Não é necessário, nem permitido, configurar chave JSON de Service Account.

## Instalação e verificações locais

No diretório-raiz do repositório:

```powershell
uv sync
uv run pytest -v
git diff --check
git status --short --branch
```

Os testes unitários e de protocolo MCP devem continuar independentes de uma
chamada administrativa real ao Google. `tests/test_dwd_directory.py` é um
diagnóstico manual de integração, não deve ser convertido em parte obrigatória
da suíte rotineira sem uma decisão explícita.

Para checar sintaxe de módulo modificado:

```powershell
uv run python -m py_compile src/google_workspace_admin/<modulo>.py
```

## Iniciar o MCP local

```powershell
uv run python -m google_workspace_admin.server
```

O transporte é `stdio`. Uma configuração de cliente Codex deve iniciar esse
comando a partir da raiz deste repositório e não deve conter tokens OAuth,
chaves de Service Account ou o conteúdo da ADC. Não sobreponha configurações MCP
preexistentes do usuário ao registrar este servidor.

## Validação estrutural do servidor MCP

Antes de considerar concluída uma alteração em `server.py`, confirme:

1. somente funções intencionalmente expostas possuem `@mcp.tool()`;
2. serializadores e helpers não possuem `@mcp.tool()`;
3. todas as ferramentas são definidas antes da inicialização do servidor;
4. `if __name__ == "__main__":` e `mcp.run()` permanecem no final absoluto de
   `server.py`;
5. não existe definição de tool, serializer, helper ou lógica de registro após
   `mcp.run()`;
6. não há saída diagnóstica arbitrária em `stdout`.

A posição de `mcp.run()` é funcional. Ao iniciar
`python -m google_workspace_admin.server`, o processo bloqueia no servidor. Uma
tool definida abaixo desse ponto pode aparecer quando o módulo é apenas
importado em um teste e ainda assim não existir no catálogo do processo real.

Ao alterar o catálogo, valide `tests/test_mcp_protocol.py`, a suíte completa e,
quando necessário, a enumeração real das tools. Confirme também que
helpers/serializers não foram expostos acidentalmente.

## Operação Directory consolidada

As tools `workspace_users_list`, `workspace_groups_list`,
`workspace_group_members_list`, `workspace_mobile_devices_list`,
`workspace_chromeos_devices_list`, `workspace_roles_list` e
`workspace_role_assignments_list` processam uma única página por chamada.
`max_results` é encaminhado como `maxResults`, `page_token` como `pageToken` e
`nextPageToken` retorna como `next_page_token`; não existe auto-pagination ou
segunda chamada implícita. O limite permanece específico de cada endpoint:
users 100, groups/members 200, mobile 100, ChromeOS 300 e roles/assignments
100.

`page_token` deve ser `None` ou uma string não vazia. String vazia,
whitespace-only e outros tipos são rejeitados. `max_results` rejeita bool,
float, string numérica, valores menores que 1 e valores acima do limite da
API. Shapes inesperados de listas ou tokens retornam erro seguro, sem body,
headers, query sensível ou material de autenticação. Chamadas HTTP Directory
consolidadas usam timeout explícito de 30 segundos, sem retry oculto.

O CODE TARGET de scopes READ é `admin.directory.user.readonly`,
`admin.directory.group.readonly`, `admin.directory.group.member.readonly` e
`admin.directory.orgunit.readonly` para users, groups, group members e
orgunits, respectivamente. A migração DWD manual foi confirmada pelo usuário
e as quatro validações reais readonly passaram. Alterações futuras de DWD
continuam sendo manuais e fora do escopo do agente.

IDs de dispositivo, serial, IMEI/MEID, MAC, localização anotada e usuário
anotado de Mobile/ChromeOS são preservados deliberadamente para inventário
administrativo. Esses campos devem ser tratados como potencialmente sensíveis.
Os valores de parâmetros de Admin Audit também podem ser dados administrativos
potencialmente sensíveis; o contrato da tool não é redesenhado nesta etapa.

O timeout do `Request()` usado pela ADC permanece fora desta consolidação:
`DEFER / requires library behavior verification`.

## Operação de Buildings paginada

`workspace_buildings_list` é uma consulta somente de leitura à coleção
`resources.buildings` da Admin SDK Directory API. Ela retorna
`{"buildings": [...], "next_page_token": ...}`; trate `next_page_token` como
opaco e repasse-o somente como `page_token` em uma chamada posterior. A tool
valida `max_results` de 1 a 500 e não executa retries nem percorre páginas
automaticamente nesta entrega.

Os testes locais usam mocks e não requerem DWD. Antes de qualquer validação
real, confirme que a DWD autoriza
`https://www.googleapis.com/auth/admin.directory.resource.calendar.readonly`
e que o sujeito delegado possui **Calendar > View Resources**. Não habilite a
Google Calendar API para essa integração.

Em 11/09/2026, essas duas confirmações administrativas foram fornecidas para
Buildings. Depois da reautenticação manual da ADC pelo usuário, um processo
MCP novo confirmou a descoberta da 13ª tool e a única chamada real limitada
foi bem-sucedida: zero Buildings e nenhuma página seguinte. Não houve
paginação, retry ou registro de dados administrativos. Uma reautenticação da
ADC é uma ação local do usuário quando necessária; não altere IAM, DWD, scopes
ou Admin Console como parte desse diagnóstico.

## Operação de Resources / Salas paginada

`workspace_calendar_resources_list` consulta somente a coleção
`resources.calendars` da Admin SDK Directory API e retorna
`{"resources": [...], "next_page_token": ...}`. Ela usa o mesmo scope readonly
de recursos de Calendar já documentado para Buildings, valida `max_results` de
1 a 500 e não percorre páginas nem cria retries.

`page_token`, `order_by` e `query` são opcionais, mas não podem ser vazios ou
conter apenas whitespace. Os valores válidos são encaminhados, respectivamente,
como `pageToken`, `orderBy` e `query`; use somente a sintaxe documentada pela
Directory API para ordenação e filtro. `next_page_token` é opaco e só deve ser
repassado como `page_token` em uma consulta posterior autorizada.

Além dos testes unitários e de protocolo MCP com mocks, em 11/09/2026 um
processo MCP `stdio` novo redescobriu as 14 tools sem expor helpers e concluiu a
única validação real autorizada de Resources / Salas com `max_results=1`. A
cadeia keyless foi bem-sucedida, retornando zero recursos e nenhuma página
seguinte; não houve paginação, retry ou registro de dados administrativos.

Antes de uma nova validação real autorizada, confirme o scope readonly já
documentado e o privilégio delegado **Calendar > View Resources**; o agente não
deve alterar DWD, IAM, APIs, scopes nem o Admin Console.

## Operação de Features paginada

`workspace_calendar_features_list` consulta somente a coleção
`resources.features` da Admin SDK Directory API e retorna
`{"features": [...], "next_page_token": ...}`. Ela usa o mesmo scope readonly
de recursos de Calendar, valida `max_results` de 1 a 500 e aceita somente o
`page_token` opcional não vazio. A API não documenta `orderBy` ou `query` para
essa operação; a tool não expõe esses parâmetros, não percorre páginas e não
cria retries.

A implementação e os testes locais usam mocks. Em 11/09/2026, a ADC foi
confirmada de modo seguro e um processo MCP `stdio` novo redescobriu as 15
tools sem expor helpers/serializers. A única chamada real autorizada,
`workspace_calendar_features_list(max_results=1)`, concluiu a cadeia keyless
com sucesso, retornando zero Features e sem página seguinte. Não houve
paginação, retry, alteração administrativa nem registro de dados de Feature ou
material de autenticação.

Com o checkpoint de Features, o bloco Calendar — recursos corporativos está
encerrado. Qualquer nova operação real deve continuar sendo autorizada
explicitamente e limitada à necessidade da entrega correspondente.

## Operação de Admin Audit paginada

`workspace_admin_audit_list` consulta apenas
`/admin/reports/v1/activity/users/{userKey}/applications/admin` da Reports API
e retorna `{"activities": [...], "next_page_token": ...}`. A aplicação
permanece fixa em `admin`; `user_key` é somente filtro de eventos e não altera o
sujeito DWD controlado por configuração. A tool limita `max_results` a 1–100
(padrão 25), aceita paginação explícita e não percorre páginas nem cria retries.

`page_token`, `event_name`, `filters`, `start_time`, `end_time`,
`actor_ip_address` e `org_unit_id` são opcionais, mas não podem ser vazios.
Datas devem ter formato RFC 3339 e `start_time` deve anteceder `end_time` quando
ambos forem informados. O MCP não encaminha `customerId` ou
`includeSensitiveData`; também nunca serializa `sensitiveParameters`.

Os testes locais usam mocks e não requerem DWD. Em 11/09/2026, após confirmação
manual da DWD `https://www.googleapis.com/auth/admin.reports.audit.readonly` e
do sujeito delegado Superadministrador, a REAL VALIDATION foi executada uma
única vez pelo launcher Python da `.venv`: a chamada MCP retornou 1 Activity e
`next_page_token` presente. Nenhum conteúdo da Activity foi registrado. As
tentativas anteriores em `codexsandboxoffline` foram restrições de transporte,
socket ou cache do `uv`; não foram falhas comprovadas da API. Não altere DWD,
IAM, APIs, scopes, privilégios, Google Cloud ou Admin Console; qualquer
reautenticação ADC continua manual pelo usuário. O checkpoint Git desta
entrega está concluído.

## Operação de Login Audit paginada

`workspace_login_audit_list` consulta apenas
`/admin/reports/v1/activity/users/{userKey}/applications/login` da Reports API.
`applicationName=login` permanece fixo; `user_key` filtra as atividades e não
altera o sujeito DWD. O scope é
`https://www.googleapis.com/auth/admin.reports.audit.readonly`.

A tool limita `max_results` a 1–100 (padrão 25), aceita paginação explícita e
preserva `nextPageToken` como `next_page_token`, sem percorrer páginas e sem
criar retries. `page_token`, `event_name`, `filters`, `start_time`, `end_time`,
`actor_ip_address` e `org_unit_id` não podem ser vazios. Datas devem estar em
RFC 3339 e `start_time` deve anteceder `end_time` quando ambos forem
informados. `customerId`, `includeSensitiveData` e os filtros genéricos de
recursos, status, OAuth, rede, agentes e dispositivos não são encaminhados.

O serializer conserva somente campos administrativos necessários e valores
allowlisted de login. E-mails afetados, timestamps internos, ações sensíveis,
`sensitiveParameters`, `resourceIds`, status bruto, metadados, payload bruto e
material de autenticação nunca são expostos.

Os testes locais usam mocks e não requerem DWD. O scope já presente no DWD e o
privilégio delegado foram mantidos sem alteração. Em 11/09/2026, a REAL
VALIDATION foi concluída pelo MCP carregado pelo host com exatamente uma chamada
`workspace_login_audit_list(max_results=1)`, sem `gcloud`, REST paralelo, retry ou
paginação: retornou 1 Activity e `next_page_token` presente. Nenhum conteúdo de
Activity, PII, credencial ou token foi registrado; a evidência cobre uma única
página/chamada operacional e não todos os tipos de eventos Login.

## Operação de Drive Audit paginada

`workspace_drive_audit_list` consulta somente
`/admin/reports/v1/activity/users/{userKey}/applications/drive` da Reports API.
`applicationName=drive` é fixo; `user_key` filtra as atividades e não altera o
sujeito DWD. O scope é
`https://www.googleapis.com/auth/admin.reports.audit.readonly`, já utilizado
por Admin Audit e Login Audit.

A tool limita `max_results` a 1–100, padrão 25, aceita `page_token` explícito e
retorna somente uma página por chamada. `nextPageToken` é convertido para
`next_page_token`; não há auto-paginação, loop oculto ou retry automático. O
timeout HTTP permanece em 30 segundos e respostas HTTP não-2xx são propagadas
com `raise_for_status()`.

`page_token`, `user_key`, `event_name`, `filters`, `start_time`, `end_time`,
`actor_ip_address` e `org_unit_id` não podem ser vazios ou conter somente
whitespace. Datas devem ser RFC3339 e `start_time` deve anteceder `end_time`
quando ambas forem fornecidas. Uma única extremidade temporal pode ser omitida,
conforme permitido pela API. Não é aplicado limite local artificial de 180 dias:
a documentação operacional preserva separadamente a janela de relatório de até
180 dias e a retenção geral de seis meses.

O serializer de Drive não repassa a Activity original. Ele usa allowlist para
timestamp, qualificador, tipo/nome do evento, categorias operacionais, ator/IP
e IDs opacos necessários à correlação. Valores de títulos, owners,
destinatários, queries, URLs, conteúdo e labels ficam omitidos; estruturas como
`sensitiveParameters`, `resourceIds`, `resourceDetails`, `networkInfo`,
`userDeviceInfo`, OAuth, dados agentic, `kind`, `etag`, `ownerDomain` e campos
desconhecidos não são retornados.

Os testes locais são mockados e não substituem a validação real. Em 11/09/2026,
após autorização explícita, a REAL VALIDATION foi concluída exclusivamente pelo
MCP original carregado pelo host com exatamente uma chamada
`workspace_drive_audit_list(max_results=1)`: sucesso, 1 Activity e
`next_page_token` presente. A cadeia Codex host → MCP stdio → Python `.venv` →
ADC → IAM `signJwt` → DWD/OAuth → Reports API → `activities.list` com
`applicationName=drive` foi validada; não houve retry nem paginação adicional,
e nenhum conteúdo real de Activity foi persistido. O checkpoint Git desta
entrega é concluído com o commit autorizado após as verificações finais.

## Operação de User Usage paginada

`workspace_user_usage_get` consulta somente
`/admin/reports/v1/usage/users/{userKey}/dates/{date}` pelo método
`userUsageReport.get`, usando o scope
`https://www.googleapis.com/auth/admin.reports.usage.readonly`. `date` é
obrigatório, estritamente `YYYY-MM-DD` e deve ser uma data válida.

`max_results` é limitado a 1–100, padrão 25. `page_token`, `parameters`,
`filters` e `org_unit_id` são opcionais, mas não podem estar vazios;
`org_unit_id` é encaminhado como `orgUnitID`. Cada chamada faz exatamente um
GET com timeout de 30 segundos, não envia `customerId`, não cria retries e não
percorre páginas automaticamente. `nextPageToken` é devolvido como
`next_page_token` para uma chamada posterior.

O serializer devolve somente `date`, `profile_id` derivado de
`entity.profileId` e parâmetros explicitamente allowlisted. Omite
`userEmail`, `entityId`, `customerId`, `kind`, `etag`, payload bruto,
`stringValue`/`msgValue` genéricos e parâmetros desconhecidos. Os timestamps de
Accounts `timestamp_creation`, `timestamp_last_login` e `timestamp_last_sso`
só são serializados quando o nome correspondente estiver explicitamente em
`parameters`. Warnings são reduzidos a `warnings_present` e
`warnings_count`.

Os testes locais desta etapa usam exclusivamente mocks. A REAL VALIDATION final
foi executada em `2026-09-12` pelo MCP original com uma única chamada para a
data do relatório solicitado `date=2026-09-10`, `max_results=1`,
`parameters=accounts:used_quota_in_percentage` e `user_key=all`: sucesso,
`usageReports=1`, `next_page_token` presente, `warnings_present=true`,
`warnings_count=1`, sem retry e sem paginação adicional.

### Lição operacional: autenticação ADC local

Quando uma nova chamada Workspace falhar de forma opaca na camada de
autenticação, verifique a ADC e faça a reautenticação local antes de alterar
DWD, scopes ou privilégios. O procedimento manual permitido ao operador é:

```powershell
gcloud auth application-default login
gcloud auth application-default print-access-token > $null
if ($LASTEXITCODE -eq 0) { "ADC_OK" } else { "ADC_FALHOU" }
```

O segundo comando valida a ADC sem imprimir o token. Isso é reautenticação
local da ADC, não renovação manual do token DWD e não exige chave JSON de
Service Account. Alterações no Google Admin Console, Google Cloud, IAM, DWD ou
scopes continuam exclusivamente manuais; Codex/MCP não deve executá-las.

A instrumentação diagnóstica temporária usada nesta investigação foi removida
completamente e não é procedimento operacional normal. Campos diagnósticos
temporários também não fazem parte do contrato final da ferramenta.

### Diagnóstico estruturado e seguro de erros

As tools Directory consolidadas e o caminho DWD correspondente propagam falhas
conhecidas com um contrato interno curto e determinístico: `code`, `layer`,
`operation` e `http_status`. A mensagem também contém somente esses metadados,
para que o host possa classificá-la mesmo quando não preservar os atributos da
exceção. As categorias atuais são:

- `ADC_REFRESH`: falha ao renovar credenciais ADC localmente;
- `IAM_SIGN_JWT`: falha HTTP ou de transporte no `signJwt` do IAM;
- `DWD_TOKEN_EXCHANGE`: falha HTTP ou de transporte na troca OAuth DWD;
- `WORKSPACE_HTTP`: falha HTTP, timeout ou transporte na Workspace API;
- `RESPONSE_VALIDATION`: JSON, shape ou token de página inesperado após a
  resposta;
- `LOCAL_VALIDATION`: argumento local inválido;
- `UNEXPECTED_LOCAL`: falha local não prevista, sem texto da exceção original.

O diagnóstico operacional deve registrar apenas a categoria, a camada, a
operação segura e o status HTTP quando disponível. Não se deve registrar ou
retransmitir body, `response.text`, headers, URL completa, query sensível,
token, JWT, credencial ou registro de usuário. Não há persistência em arquivo,
telemetria, `print()` ou retry implícito. `ADC_REFRESH` requer ação manual do
operador; `WORKSPACE_HTTP` deve ser separado de `RESPONSE_VALIDATION`, e
nenhuma falha autoriza paginação ou nova tentativa automática.

## Operação de Customer Usage

`workspace_customer_usage_get` consulta
`/admin/reports/v1/usage/dates/{date}` pelo método
`CustomerUsageReports.get`, usando o scope
`https://www.googleapis.com/auth/admin.reports.usage.readonly`. `date` é
obrigatório, estritamente `YYYY-MM-DD` e representa somente a data solicitada
do relatório.

`parameters` é obrigatório e deve conter um CSV de métricas totalmente
qualificadas da allowlist inicial de Accounts. A validação rejeita valores
ausentes/vazios, tokens vazios, wildcard, aplicação inteira, nomes
desconhecidos, deprecated e duplicatas; normaliza apenas espaços externos e
preserva a ordem. Não existe modo implícito de solicitar todas as métricas.

`page_token` é opcional e é encaminhado como `pageToken`. A tool executa uma
única requisição por invocation, devolve `nextPageToken` como
`next_page_token`, não percorre páginas automaticamente, não cria retries e usa
timeout de 30 segundos. Não envia `customerId`, `maxResults`, `userKey`,
`filters` ou `orgUnitID`.

O serializer preserva apenas `date` e métricas integer solicitadas e
allowlisted. Omite integralmente entity, identificadores, `kind`, `etag`,
`stringValue`, `datetimeValue`, `msgValue`, `boolValue`, warnings brutos e o
payload bruto. Warnings são reduzidos a `warnings_present` e
`warnings_count`. O catálogo tem 20 tools após o IMPLEMENT; a REAL VALIDATION
V9 de Customer Usage foi concluída anteriormente. Esta IMPLEMENT não executa
nova validação real.

## Testes de integração Google

Faça-os apenas quando a tarefa requerer validação real e houver autorização
expressa. O ciclo seguro é:

1. executar uma ferramenta ou chamada de leitura limitada;
2. registrar somente operação, status HTTP e contagem relevante;
3. confirmar que a resposta passa pelo serializador MCP;
4. nunca salvar payload bruto, token ou cabeçalho;
5. atualizar a árvore de fases com a evidência.

Sinais de falha e primeira verificação:

| Sintoma | Verificar sem expor segredos |
| --- | --- |
| ADC inválida | autenticação Application Default Credentials local e política organizacional |
| `signJwt` negado | permissão IAM na Service Account para a identidade ADC |
| DWD/OAuth negado | Client ID da Service Account, scope exato e propagação no Admin Console |
| 403 Directory/Reports | privilégio do sujeito delegado, API habilitada e scope da operação |
| ferramenta não aparece no Codex | processo MCP antigo, registro da ferramenta e reinicialização/redescoberta |
| tool esperada ausente no processo real | posição relativa a `mcp.run()`, decorador e registro |
| serializer/helper aparece como tool | `@mcp.tool()` aplicado indevidamente a função auxiliar |
| testes/import mostram tool, mas Codex não | validar catálogo direto; se correto, reiniciar/redescobrir antes de editar código |

## Verificações antes do commit

Depois dos testes e da documentação:

```powershell
git diff --check
git status --short
```

Revise o diff e faça staging somente dos arquivos da entrega. Depois execute:

```powershell
git diff --cached --check
git diff --cached --stat
```

Somente crie o checkpoint quando os testes e verificações aplicáveis estiverem
aprovados. Warnings de conversão de line endings do Git devem ser tratados
separadamente de erros reais de whitespace; não altere globalmente
`core.autocrlf` ou `.gitattributes` no meio de uma entrega sem uma decisão
específica para normalização do repositório.

## Definição de pronto para uma ferramenta de leitura

- documentação oficial da API, endpoint e scope revisados;
- DWD alterada somente se necessária e autorizada;
- módulo HTTP com timeout, validação e resposta limitada;
- serializador MCP explícito;
- teste unitário e teste pelo protocolo MCP;
- `uv run pytest -v` e `git diff --check` aprovados;
- integração real aprovada quando aplicável;
- catálogo, histórico e árvore de fases atualizados.

Operações de escrita pertencem à FASE 2 e exigem validação adicional,
confirmação explícita do alvo e salvaguardas contra ação destrutiva. Não
implemente uma ferramenta de escrita como extensão implícita de uma consulta.

## Fase 1.5 — Foundation Content Implement V1

A Foundation Content é uma camada transversal local, sem chamadas Google e
sem registro MCP. Ela mantém profiles de autenticação imutáveis, subjects
canônicos, registry fechado de scopes read-only, guard positivo de operações,
transport mockável, paginação bounded, limites de contexto, evidência e erros
seguros.

As operações futuras de Shared Drive (`drive.list`, `drive.get` e
`drive.files.list`) existem somente como contratos internos. O modo
`useDomainAdminAccess` permanece explicitamente opt-in, `files.list` usa o
contrato de um único drive e nenhuma operação aceita método mutável ou
paginação ilimitada. A Foundation não executa Directory lookup, DWD, IAM
`signJwt`, troca de token ou HTTP real.

Para testar a Foundation sem alterar a Read Layer atual:

```powershell
.venv\Scripts\python.exe -m pytest -q tests\test_content_foundation.py
```

O teste de transporte usa `httpx.MockTransport`; nenhuma rede é necessária.

## Fase 1.5 — Foundation Remediation Implement V1

A remediação deve ser verificada localmente com:

```powershell
.venv\Scripts\python.exe -m pytest -q tests\test_content_foundation.py tests\test_content_auth_boundary.py tests\test_content_transport_security.py
.venv\Scripts\python.exe -m pytest -q
git diff --check
```

Os testes da Foundation não devem executar rede, Google APIs, DWD, IAM
`signJwt`, ADC ou MCP funcional. O client de produção não aceita injeção de
`httpx.Client`; naquele contrato V1 os testes usavam a construção interna
`_for_test`, removida e superada pela Remediation V3. Não registrar ou exibir
tokens, JWTs, headers, payloads brutos, corpos de documentos ou queries livres.

O próximo passo da Fase 1.5 é `FOUNDATION REVIEW V2`. Nenhuma tool Shared
Drive, Gmail ou Write deve ser registrada antes de revisão e autorização
separadas.

## Fase 1.5 — Foundation Remediation Implement V2

A cadeia local obrigatória para os contratos Content internos é:

```text
trusted startup provisioning
  -> ContentProfileRegistry
  -> RegisteredProfileHandle
  -> SubjectResolver
  -> AuthorizedSubjectHandle
  -> ContentAuthBroker
  -> AuthorizedOperationContext
  -> normalized operation
  -> ContentReadTransport
  -> typed Drive result
```

`ContentAuthProfile` e `WorkspaceSubject` são somente dados imutáveis; não
devem ser passados como autoridade. O runtime seleciona um profile já
provisionado, o resolver emite a authority do subject e o broker emite o
contexto da operação. Qualquer contexto fabricado, operação sem broker,
scope/capability incompatível ou modo administrativo não autorizado deve
falhar antes de HTTP.

Os contratos `drive.list`, `drive.get` e `drive.files.list` continuam internos
e não registrados no MCP. `max_items` reduz efetivamente o `pageSize`; uma
resposta acima do contrato é rejeitada, sem slicing silencioso ou token de
continuação local. O resultado público da camada Content é tipado e
allowlistado, sem `dict` Google genérico, headers, corpo de erro ou
`httpx.Response`.

Os testes devem ser executados localmente com a `.venv`, usando
`httpx.MockTransport`, sem rede, Google API, DWD, IAM `signJwt`, ADC ou chamada
MCP funcional. O warning conhecido de criação do cache pytest por permissão
local não altera o resultado dos testes.

## Fase 1.5 — Foundation Remediation Implement V3

O contrato canônico local passa a ser:

```text
startup providers internos
  -> authority kernel em closure
  -> profile handle sem dados
  -> subject handle sem dados
  -> broker context sem dados
  -> request tipado exato
  -> operação GET normalizada internamente
  -> HTTP adapter específico da operação
  -> DTO tipado allowlistado
```

O runtime de produção é criado somente por `create_content_runtime()` sem
argumentos. Como Content Research ainda não foi provisionado, esse bootstrap
falha de modo seguro antes de HTTP. Nos testes, o harness
`tests/content_runtime_harness.py` substitui providers/factories antes da
montagem e usa `httpx.MockTransport`; não existe attach ou substituição do
client depois que o runtime foi criado.

Validação local desta remediação:

```powershell
.venv\Scripts\python.exe -m pytest -q tests\test_content_foundation.py tests\test_content_auth_boundary.py tests\test_content_transport_security.py
.venv\Scripts\python.exe -m pytest -q
git diff --check
```

Esses comandos não devem fazer chamadas Google, MCP funcionais, token, DWD,
IAM `signJwt` ou ADC. O próximo passo é uma Review V4 independente; não
registre tools Drive antes dessa autorização e revisão.

## Fase 1.5 — Foundation Remediation Implement V4

A Remediation V4 mantém o composition root como único wiring suportado. O
runtime não possui setters, attach de client, executor substituível ou
componentes caller-supplied. O harness de testes substitui providers somente
antes da montagem e continua usando `httpx.MockTransport`.

Os testes V4 devem cobrir runtime fabricado, subclassificação, requests
normalizados sem destino HTTP, client injection, subclasses de limites/retry,
ceilings no consumo, campos categóricos de auditoria, resposta tipada e
invariante estrita de `trashed`. A execução continua exclusivamente local,
sem Google, Directory, MCP funcional, tokens, DWD, IAM ou ADC.

Boundary documentada:

```text
IN SCOPE:  untrusted MCP/runtime inputs; supported Content API
OUT:       arbitrary Python execution/monkeypatch após comprometimento,
           debugger, memory manipulation e closure mutation deliberada
```

## Fase 1.5.1 — Shared Drive Discovery — operação local

O IMPLEMENT V1 registra duas tools Content read-only:
`workspace_drives_list` e `workspace_drive_get`. O catálogo esperado é de 22
tools: 20 Read históricas, Content = 2 e Write = 0. Não existe
`workspace_drive_files_list`; seus contratos internos permanecem reservados
para 1.5.2.

O bootstrap Content continua lazy. `tools/list`, import do servidor e testes de
schema não criam runtime, não consultam ADC e não fazem rede. O runtime só é
criado na primeira invocação funcional e falha fechado enquanto o Content
Research provisioning não estiver disponível.

### Contratos e limites

`workspace_drives_list` aceita `page_size` e `max_items` estritos entre 1 e
100, com defaults 25 e 100; o adapter envia o mínimo dos dois. `page_token` é
`None` ou string opaca não vazia. Uma invocation faz no máximo um GET e só
repassa `nextPageToken` validado pelo Google. O retorno contém apenas
`drive_id`, `name` e `next_page_token`, preservando nomes duplicados.

`workspace_drive_get` aceita `drive_id` estrito, com trim boundary, 1–256
caracteres, sem whitespace ou controles. O ID é operacional e é codificado
como um único path segment; nome nunca é usado para lookup ou desambiguação.
O retorno contém somente `drive: {drive_id, name}`.

O modo `use_domain_admin_access` permanece `false` por padrão e somente pode
ser encaminhado quando o profile, subject, capability `DRIVE`, capability
administrativa `SHARED_DRIVE_DISCOVERY` e compatibilidade da operação forem
validados. A flag não concede acesso universal ao conteúdo.

### Testes locais sem Google

Use a `.venv` e mantenha todas as dependências externas mockadas:

```powershell
.venv\Scripts\python.exe -m pytest -q tests\test_shared_drive_discovery.py tests\test_content_keyless.py
.venv\Scripts\python.exe -m pytest -q tests\test_content_foundation.py tests\test_content_auth_boundary.py tests\test_content_transport_security.py tests\test_mcp_protocol.py
.venv\Scripts\python.exe -m pytest -q
git diff --check
```

Os testes usam `httpx.MockTransport` e ports/fakes locais para ADC, `signJwt`,
OAuth e token. É proibido que a suíte routine chame `google.auth.default`,
metadata server, `gcloud`, IAM Credentials, endpoint OAuth ou Drive API.
Valide também catálogo único, schemas estritos, duplicate names, stable IDs,
admin default, mismatch administrativo antes do HTTP, fields/host/método
fixos, parser allowlisted, erros sem body e ausência de rotas de mutação.

### Gate de autenticação e provisioning manual

O estado esperado desta implementação é `Google activity = 0` e `ADC activity
= 0`. Antes da primeira REAL VALIDATION, o operador deverá executar
manualmente o provisioning documentado em `docs/01_GOOGLE_CONFIGURATION.md`:
Drive API habilitada, Content Research Service Account separada, permissão
IAM restrita para `signJwt`, DWD separada com exatamente
`https://www.googleapis.com/auth/drive.readonly`, sujeito delegado e policy
fixos. Codex/MCP não executa nenhuma alteração em Cloud, IAM, Service Account,
Admin Console, DWD, scopes ou APIs.

O fluxo de identidade é:

```text
ADC local -> IAM Credentials signJwt -> Content Research SA -> DWD -> OAuth -> Drive API
```

ADC válida sozinha não prova existência da Content SA, permissão IAM,
autorização DWD, sujeito delegado ou scope Drive. Se uma etapa REAL VALIDATION
exigir `gcloud auth application-default login`, aplique o stop obrigatório:

```text
BEFORE ANY COMMAND REQUIRING: gcloud auth application-default login
STOP AND ASK OPERATOR FOR EXPLICIT AUTHORIZATION.
```

Se a ADC estiver expirada, reporte `ADC reauthentication required`, forneça o
comando exato ao operador, pare e aguarde. Nunca execute login automaticamente.

### Histórico de REAL VALIDATION

RV1 não fez operação Google: o precheck de configuração falhou no caminho
direto Python/PowerShell, que não herdava o ambiente próprio do MCP. Diagnostic
V1 confirmou que a configuração e o provisioning locais estavam corretos e
isolou a causa na boundary de execução.

RV2 usou exclusivamente a instância MCP hospedada e fez uma única chamada
bounded de `workspace_drives_list` em modo administrativo `false`. A cadeia
keyless passou até a Drive API; o resultado seguro registrou somente uma
contagem de Shared Drives e a presença de próxima página. Não houve retry,
paginação adicional, mutação ou exposição de payload, token, JWT, Authorization
ou ADC. Não repita essa validação sem nova autorização explícita.

## Fase 1.5.1 — Operational Auth Binding — operação local

O runtime Content usa configuração process-only. Antes de qualquer operação
funcional, o operador deverá fornecer as cinco variáveis abaixo; o
`customer_id` é obrigatório e não pode ser substituído por `my_customer`:

```powershell
$env:GOOGLE_WORKSPACE_CONTENT_PROJECT_ID = "codex-workspace-admin"
$env:GOOGLE_WORKSPACE_CONTENT_SERVICE_ACCOUNT = "codex-workspace-content@codex-workspace-admin.iam.gserviceaccount.com"
$env:GOOGLE_WORKSPACE_CONTENT_SUBJECT = "suporte.ti@cevalente.com.br"
$env:GOOGLE_WORKSPACE_CONTENT_CUSTOMER_ID = "<CUSTOMER_ID_A_FORNECER>"
$env:GOOGLE_WORKSPACE_CONTENT_DOMAIN = "cevalente.com.br"
```

O bloco é uma instrução futura e não foi aplicado automaticamente. Não use
`.env`, ambiente persistente do Windows ou `local workstation path (omitted)`
para armazenar essa configuração sem uma decisão operacional separada. Não
adicione variável de scope ou Client ID DWD.

O binding segue `ADC -> IAM signJwt -> DWD -> OAuth`, mas ADC só é acessada
quando uma operação Content precisar de token. Import, startup, `tools/list`,
parsing de configuração e testes locais não acessam ADC. Os testes usam
fakes/`httpx.MockTransport` para ADC, IAM, OAuth e Drive.

O operador confirmou manualmente Content SA, IAM Token Creator e DWD com
`drive.readonly`. Para a RV2 autorizada, as cinco variáveis obrigatórias,
incluindo `customer_id`, foram fornecidas na tabela de ambiente do MCP. A
validação real passou uma única vez pelo host MCP; não consulte o ambiente do
host por subprocesso para inferir essa configuração.

### Gate obrigatório antes da RV1

Antes de qualquer comando que requeira:

```text
gcloud auth application-default login
```

aplicar:

```text
STOP AND ASK OPERATOR FOR EXPLICIT AUTHORIZATION.
```

Se a ADC estiver expirada, informar `ADC reauthentication required`, fornecer
o comando exato e aguardar o operador. Não executar login, `signJwt`, OAuth ou
Drive automaticamente.

## Fase 1.5.2 — Drive File Inventory — operação local

O IMPLEMENT V1 registra `workspace_drive_files_list` com somente `drive_id`,
`page_size`, `page_token` e `max_items`. Cada chamada representa no máximo uma
página de `files.list`; não há recursão, export, download, leitura de conteúdo
ou paginação automática. O hard cap Content é 500 e o adapter sempre envia o
menor entre `page_size`, `max_items` e 500.

O request é fixo em HTTPS, host Google, GET e `/drive/v3/files`, restringido ao
Shared Drive por `corpora=drive`, `driveId`, `spaces=drive`,
`includeItemsFromAllDrives=true`, `supportsAllDrives=true` e
`q=trashed = false`. O resultado expõe somente ID, nome, MIME type, modified
time opcional, size opcional, parents e next-page token. Folders permanecem no
inventário; MIME não é inferido por extensão.

Para validar localmente sem Google:

```powershell
.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_drive_file_inventory.py
.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_shared_drive_discovery.py tests\test_content_operational_auth.py
.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_content_foundation.py tests\test_content_transport_security.py tests\test_mcp_protocol.py
.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

O resultado desta implementação foi **747 passed**, usando apenas mocks/fakes.
A REAL VALIDATION RV2 autorizada ocorreu exclusivamente pelo MCP hospedado:
uma descoberta bounded e uma página bounded de inventário, sem retry,
continuação ou exposição de IDs/metadados. `REAL VALIDATION = PASS`; não
repita chamadas reais sem autorização explícita para uma etapa posterior.

## Fase 1.5.3 — Content Reading Architecture & Safety — operação local

PLAN V1 = **COMPLETE**; IMPLEMENT V1 = **COMPLETE** para o substrate comum.

O IMPLEMENT V1 desta etapa é local e não registra nova tool. Os módulos
internos de substrate validam MIME, snapshots, budgets, chunks, provenance,
outcomes e preflight sem aceitar host, URL, método, scope, parser executable ou
export MIME fornecido pelo caller.

Requisito obrigatório de compliance: o projeto deve ser capaz de processar o
conteúdo de todos os arquivos inventariados relevantes, incluindo Google Docs,
Google Sheets, Google Slides, PDFs, documentos Microsoft Office e formatos
textuais, registrando explicitamente todo arquivo que não puder ser processado.
Isso exige routing e um outcome terminal por arquivo; não exige interpretar
bytes arbitrários nem autoriza execução de conteúdo.

Os budgets padrão são finitos: download 32 MiB, export 8 MiB, parser input 32
MiB, conteúdo extraído 2 MiB, chunk textual 256 KiB, chunk estruturado 1 MiB,
archive descomprimido 64 MiB, 10.000 membros, timeout de parser 15 s por chunk e
30 s por arquivo. O primeiro limite atingido não encerra automaticamente o
arquivo: continuação segura produz `PARTIALLY_PROCESSED`; somente limite
absoluto ou continuação impossível produz `TOO_LARGE`.

Para validação local use apenas a suíte de substrate e as suítes Foundation
existentes, sempre com mocks/fakes e sem ADC, Google, IAM ou OAuth. Readers
concretos e REAL VALIDATION exigem autorização própria em etapa posterior.

FINAL REVIEW V1 desta etapa foi concluído localmente com 80 testes targeted,
207 testes no grupo reconciliado de Foundation/security/protocol e 827 na
regressão completa. A diferença histórica 207 versus 187 foi somente a
composição do comando: os 20 testes de `test_content_auth_boundary.py` não
foram incluídos no relatório de IMPLEMENT; nenhum teste foi perdido.
Não existe operação Google executável em 1.5.3, portanto REAL GOOGLE VALIDATION
= NOT APPLICABLE / NOT EXECUTED. FINAL REVIEW V1 = **COMPLETE** e CHECKPOINT
V1 = **COMPLETE**; readers concretos somente poderão começar após autorização
explícita da etapa 1.5.4.

## Fase 1.5.4 — Google Docs Content — operação local

`workspace_file_content_read` exige `file_id`, `expected_mime_type` e
`modified_time`; `continuation_token` é opcional. Budgets, endpoint, fields,
scope, retry e suggestions mode são políticas internas. Na entrega 1.5.4,
somente o MIME Google Docs possuía reader concreto; outros MIME routes então
terminavam explicitamente como não suportados.

O resultado mantém três responsabilidades separadas: `processing_status` é o
resultado terminal, `safe_error_code` é a classificação segura do que falhou e
`failure_stage` é um enum fechado da localização causal. Os estágios possíveis
são `PREFLIGHT_FETCH`, `PREFLIGHT_VALIDATION`, `DOCS_REQUEST`,
`DOCS_RESPONSE_TRANSPORT`, `DOCS_JSON_PARSE`, `DOCS_SCHEMA_PARSE`,
`DOCS_STRUCTURAL_EXTRACTION`, `PROVENANCE_BUILD`, `POSTFLIGHT_FETCH` e
`POSTFLIGHT_VALIDATION`. Em `PROCESSED`, `EMPTY` e `PARTIALLY_PROCESSED`, o
campo é `null`; em falha terminal, só é preenchido quando o boundary conhece a
causa de forma segura. Mensagens de exceção, response bodies, URLs e IDs nunca
são projetados no resultado MCP ou no audit.

Para Google Docs, uma invocation executa metadata Drive preflight,
`documents.get` e metadata Drive postflight. Nenhum chunk é liberado se MIME,
`modifiedTime` ou `trashed` divergirem. A resposta Docs possui dois limites
independentes de 32 MiB: representação codificada raw/wire e representação
decodificada entregue ao parser. O adapter conta `iter_raw()` antes de
decodificar e usa descompressão incremental limitada para `gzip` e `deflate`;
`identity` é direto e qualquer outro Content-Encoding falha fechado.
`Content-Length` é somente otimização de rejeição antecipada: os contadores
reais são autoritativos para header ausente, incorreto, subdeclarado ou
transferência chunked. Somente depois de comprovar o limite decodificado o JSON
é materializado. Output MCP permanece separado e bounded. `includeTabsContent`
é sempre true, suggestions são sempre inline e não existe fallback para modos
que silenciem sugestões. Comments/comment threads Developer Preview ficam fora
de 1.5.4 V1 e `commentsViewMode` não é solicitado.

Continuation é local, expira, é vinculada ao arquivo/snapshot/versão e usa
handle opaco autenticado. Reinício do processo invalida o estado; isso deve ser
tratado como validação local segura, não como cursor Google. A continuation
refaz o fetch completo e nunca é seguida automaticamente. O store RAM possui
TTL e capacidade finitos; purge, capacity check, insertion, resolve e remoção
por expiração são protegidos atomicamente por lock. O lock não atravessa I/O,
parse ou normalização, e o estado não armazena conteúdo ou resposta Google.

Objetos visuais e equations sem representação textual não recebem OCR nem
download e produzem `PARTIALLY_PROCESSED`. Hyperlinks e URIs de embedded
objects nunca são seguidos. Conteúdo como instruções, URLs ou comandos permanece
dado não confiável sob `NEVER_EXECUTE_FILE_CONTENT`.

Section breaks não geram texto. Cada boundary validada é retornada no array
bounded `structural_locations`, com provenance de tab, segmento, structural
path, índices UTF-16 e ordinal, além de IDs seguros de relação quando
aplicáveis. Um documento sem texto extraível continua `EMPTY` mesmo que possua
section boundaries; os locations não são contados como chunks de conteúdo.

Validação local, sem ADC/Google:

```powershell
.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_google_docs_content.py
.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_content_reading_substrate.py
.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_shared_drive_discovery.py tests\test_drive_file_inventory.py tests\test_content_operational_auth.py tests\test_content_keyless.py
.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_content_auth_boundary.py tests\test_content_foundation.py tests\test_content_transport_security.py tests\test_mcp_protocol.py
.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
git diff --check
```

## Fase 1.5.5 — Google Sheets Content — operação local

### Estado terminal atual — 02/10/2026

Google Sheets 1.5.5 está implementado, validado offline e validado com Google
real. A fixture está em `pt_BR` / `America/Sao_Paulo`; K1=`1234.5` é
`NUMBER / 0.00`, L1=`0.125` é `PERCENT / 0.0%`, O1 é `=SEQUENCE(1,2)` e P1 é
`EXPECTED_TRAILING_OMISSION`, sem padding sintético. O reparo canônico K1/L1 e a
validação real final estão completos; `PRODUCT DEFECT = NO` e
`PRODUCTION_READER_DEFECT = NO`.

Nenhum gate Sheets de implementação ou validação real está pendente. O
checkpoint Git atual está **STAGED / COMMIT PENDING**: 49 caminhos aprovados
staged, commit não criado e sincronização remota não realizada. Este runbook
descreve procedimentos; não autoriza commit, runner, operação Google ou outra
operação futura. A autorização específica é externa e vinculada à conversa
atual com o operador. Os ponteiros nas subseções históricas abaixo são
referências históricas, não instruções atuais.

### Histórico — direção operacional pré-rebase e limite do gate

> Snapshot histórico anterior à rebase do contrato e à validação real final.
> Os status `PENDING` e recomendações de gates Sheets abaixo foram superados
> pelos resultados de 02/10/2026; mantenha-os apenas como cronologia.

O escopo congelado é um MVP local, somente de leitura, para um operador
técnico/IT e uma organização Workspace por runtime. A evidência real mais
recente confirmou que o perfil regional canônico da fixture já é
`locale=pt_BR` e `timeZone=America/Sao_Paulo`. **Nenhum reparo regional no
Google é necessário.** O reader de produção segue locale-agnostic e
timezone-agnostic.

O gate offline de rebase do contrato foi executado e classificado **B —
HARNESS_CONTRACT_EXTENSION_REQUIRED**. A especificação e o loader locais ainda
exigem `en_US` e não representam timezone; essa implementação está obsoleta em
relação à evidência e ao requisito brasileiro, mas não foi alterada. O harness
canônico exige literais exatos de display: retirar o literal antigo de K1/L1
também retiraria a verificação da presença desses componentes. Não enfraqueça a
asserção nem mantenha `1234.50`/`12.5%` como literais brasileiros atuais. Os
registros históricos com `en_US` permanecem historicamente corretos.

O próximo gate recomendado, ainda **NOT AUTHORIZED**, é
`WORKSPACE-CONTENT-GSHEETS-PENDING-DISPLAY-HARNESS-CONTRACT-ARCHITECTURE-OFFLINE-V1`.
Ele deve decidir como o contrato/harness representa, separadamente, componente
obrigatório e literal exato pendente. Depois disso, a rebase local poderá fixar
`pt_BR` e `America/Sao_Paulo`, seguida pela leitura real read-only de K1:L1 e
O1:P1; não há escrita regional Google prevista. Escritas de células só poderão
ser avaliadas depois de evidência read-only e autorização própria.

O gate de checkpoint não está autorizado. A próxima revisão de checkpoint só
poderá ser proposta depois de todas as condições registradas em
`docs/04_PHASE_STATUS.md` serem satisfeitas.

O MIME `application/vnd.google-apps.spreadsheet` usa a mesma tool
`workspace_file_content_read`. O reader chama somente `spreadsheets.get` por
GET em `sheets.googleapis.com`, com masks fixos e uma linha por janela, até
1000 colunas. O traversal segue a ordem `SheetProperties.index`, depois row e
column ascendentes; conteúdo oculto em sheets, rows e columns não é filtrado.
Cada invocation pode solicitar no máximo 8 janelas GridData/8000 células; com
Drive preflight, uma chamada de metadata Sheets e Drive postflight, o teto é 11
chamadas de conteúdo/metadata. Metadata aceita no máximo 200 sheets; ultrapassar
o teto termina como partial de limite, sem alegar cobertura completa. Cada
resposta Sheets é limitada a 2 MiB raw e decoded antes de materializar JSON.
Células solicitadas são contadas pela área da janela mesmo quando a resposta é
sparse. O limite lógico por arquivo é 5.000.000 células e não pode ser reiniciado
por continuation.

Aplicam-se os budgets compartilhados de até 64 chunks/invocation, 256 KiB por
chunk e 2 MiB de conteúdo extraído por invocation. Continuation usa handles
opacos autenticados de uso único, até 4096 caracteres, vinculados ao arquivo,
snapshot e versão do reader; o estado é apenas local, com TTL de 15 minutos e
máximo de 1000 estados. Ao retomar, o reader refaz preflight e metadata, valida
o fingerprint estrutural e continua no próximo componente/célula sem duplicar
ou omitir conteúdo.

Para consumir a leitura bounded, o caller mantém os chunks de cada resposta
segura e usa cada token uma vez. `processing_status` e `chunk_count` descrevem
somente a invocation atual; `chunk_count` deve corresponder a `len(chunks)`.
Uma página sparse pode retornar `PARTIALLY_PROCESSED`, zero chunks e um token.
O fluxo de consumo é:

```text
agregado = []
resposta = workspace_file_content_read(...)
repetir:
    se resposta.processing_status for falha: parar e tratar a falha
    acrescentar resposta.chunks ao agregado uma única vez
    se resposta.continuation_token estiver ausente: parar
    resposta = workspace_file_content_read(..., continuation_token=token atual)
```

Sem token, `PROCESSED` ou `EMPTY` conclui com sucesso a cobertura suportada;
`PARTIALLY_PROCESSED` sem token encerra com cobertura parcial ou limite de
recurso e não deve ser promovido a sucesso integral. Falhas também não têm
token e não são conclusão bem-sucedida. Um `EMPTY` final só informa que aquela
invocation não liberou chunks: conteúdo já recebido em respostas anteriores
permanece no agregado.

Drive preflight/postflight compara `id`, `mimeType`, `modifiedTime` e `trashed`;
Drive `size` não é exigido para um arquivo Google Sheets nativo. Todos os chunks
da invocation ficam em buffer até o postflight. Divergência retorna
`CHANGED_DURING_AUDIT`, sem retry, chunks atuais ou continuation. Falhas
estruturais também descartam os chunks ainda não liberados.

`OBJECT`, `DATA_SOURCE` e Smart Chips detectados produzem coverage gap explícita;
fórmulas, hyperlinks e destinos de rich-text/chips são dados não executáveis e
nunca são seguidos. Não há export Drive, comentários API, OCR, Apps Script,
macros ou execução de fórmulas. Comentários de célula não são cobertos nem
detectáveis por este caminho Sheets API e permanecem future coverage gap; um
resultado `PROCESSED`/`EMPTY` descreve os componentes cobertos por este reader,
não uma verificação de comentários. Charts, drawings/images, slicers e outras
estruturas workbook-level também não são inspecionados por este reader de
células e permanecem future coverage gaps não detectadas. Não houve real Google
validation; ela continua pendente.

Teste focado offline de Sheets:

```powershell
.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_google_sheets_content.py
```

Antes da REAL VALIDATION de Google Docs, verificar manualmente a habilitação de
`docs.googleapis.com`. Se estiver desabilitada, somente o usuário poderá
habilitá-la após autorização específica. A validação real deve usar um único
Google Doc previamente selecionado, uma chamada bounded, sem seguir
continuation e sem reproduzir conteúdo em terminal, audit, fixtures ou Git.

Estado consolidado aceito para Docs 1.5.4: **checkpointed e real-validated**.
Os estados de bloqueios e remediações intermediários acima permanecem nos
registros históricos, mas não representam o estado atual da entrega. Sheets
1.5.5 está implementado e validado offline; a validação real final segue
**PENDING**.

## Google Docs/Sheets: pseudônimo público de `file_ref`

A leitura Docs/Sheets só libera chunks quando o bootstrap construiu o provider
compartilhado de pseudônimo. O processo MCP deve receber
`GOOGLE_WORKSPACE_CONTENT_PUBLIC_FILE_REF_HMAC_KEY_B64`, uma chave dedicada de
32 bytes codificada em Base64 padrão canônico. A mesma chave e o Customer ID
concreto produzem referências estáveis `gdrv_v1_<base64url sem padding>` por
HMAC-SHA-256 sobre o ID Drive exato e sensível a maiúsculas/minúsculas. Não
reutilize chave de continuation, credencial OAuth/DWD ou outro segredo.

A chave não é obrigatória para iniciar o runtime de Content Discovery, mas é
obrigatória para ler conteúdo Docs/Sheets. Ausente, a leitura termina com
`EXTRACTION_FAILED / CONTENT_NOT_SUPPORTED` antes de autenticação e HTTP; valor
inválido ou `file_id` começando com `gdrv_v1_` também falha fechado antes de
request. O pseudo-ID é somente identificador de saída: não existe resolver e
ele não serve como entrada de leitura.

Após o IMPLEMENT V3B, o operador provisionou a chave dedicada fora do
repositório, na configuração live do processo MCP. Nunca exiba nem versione esse
segredo. No RERUN 4, a cadeia keyless e a primeira leitura pública foram
alcançadas; a travessia parou porque o harness aplicava uma allowlist global de
textos sintéticos e rejeitou conteúdo não listado. Esse bloqueio histórico foi
corrigido no harness; a validação real final foi concluída em 02/10/2026.

Teste offline do contrato e dos readers:

```powershell
.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_content_public_file_ref.py tests\test_content_operational_auth.py tests\test_content_reading_substrate.py tests\test_google_docs_content.py tests\test_google_sheets_content.py
```

## Histórico — Google Sheets validation fixture contract V1 (superado)

> Este snapshot antecede a rebase brasileira e a validação real final. O
> `en_US`, os estados `PENDING` e os ponteiros de gate nesta seção descrevem a
> cronologia daquele contrato; não são o estado nem a operação atual.

O gate `WORKSPACE-CONTENT-GSHEETS-BRAZILIAN-REGIONAL-CONTRACT-REBASE-OFFLINE-V1`
terminou em **B — HARNESS_CONTRACT_EXTENSION_REQUIRED**. A metadata real
confirmou `locale=pt_BR` e `timeZone=America/Sao_Paulo`; nenhum reparo regional
no Google é necessário. O reader de produção continua locale-agnostic e
timezone-agnostic.

A implementação local permanece inalterada: o JSON canônico e o loader ainda
exigem `en_US` e não representam timezone. Essa exigência antiga está
**SUPERSEDED** como perfil brasileiro e impede a rebase até a decisão de
arquitetura; as ocorrências históricas continuam preservadas. O harness
canônico forma `EXPECTED` a partir de literais de `direct_expectations` e
compara o `CELL_DISPLAY` por igualdade exata. Remover o literal K1/L1 da lista
também removeria a checagem de presença. Portanto, não enfraquecer a checagem e
não inferir novos literais.

K1 mantém número `1234.5` e formato `0.00`; L1 mantém número `0.125` e formato
`0.0%`. A presença de `CELL_DISPLAY` continua obrigatória; o literal brasileiro
exato de cada célula está **PENDING_REAL_OBSERVATION**. M1 permanece uma lacuna
regional: serial, tipo efetivo, formato e interpretação de timezone não estão
definidos. O1 permanece `=SEQUENCE(1,2)`; locale não autoriza traduzir nomes de
funções ou fórmulas. P1 é resultado derivado/não authored e escrita direta é
proibida.

O driver controlado O1 permanece inalterado e em quarentena. Se uma escrita
futura se tornar necessária, exige
`REGIONAL_REQUALIFICATION_REQUIRED_BEFORE_FUTURE_REAL_WRITE`; a precondição
histórica `en_US` do driver não foi reescrita. A próxima observação de células,
depois da arquitetura e da rebase local, será read-only em K1:L1 e O1:P1.

Próximo gate recomendado, ainda **NOT AUTHORIZED**:
`WORKSPACE-CONTENT-GSHEETS-PENDING-DISPLAY-HARNESS-CONTRACT-ARCHITECTURE-OFFLINE-V1`.
Consulte a árvore canônica em `docs/04_PHASE_STATUS.md`.

## Registro histórico — contrato local anterior da fixture V1

> **Contrato existente, alvo superado:** esta seção descreve o spec/helper
> atualmente presente no worktree antes da rebase regional. A declaração
> `en_US`, as precondições e os procedimentos abaixo são históricos para esse
> contrato e não são ponteiros operacionais atuais. A rebase canônica brasileira
> depende do diagnóstico regional real e será um trabalho offline separado.

O contrato atualmente presente no worktree está em
`validation/fixtures/gsheets_validation_v1.json`. Ele declara o alias
`GSHEETS_VALIDATION_V1`, schema version `1`, fixture contract version `1`, aba
ordinal `0` e locale `en_US`. O spec não contém identidade Drive nem material de
autenticação. O loader estrito é
`validation/fixtures/fixture_contract.py`; o helper é
`validation/fixtures/setup_gsheets_validation_v1.py` e os testes locais estão
em `tests/test_gsheets_validation_v1_fixture_contract.py`.

`spec_schema_version` avança quando a forma ou interpretação do documento muda.
`fixture_contract_version` avança quando muda qualquer comportamento ou
expectativa da fixture, incluindo locale, display, valor authored, fórmula,
formato, componente ou estrutura. Mudanças somente documentais não avançam
nenhuma versão. Versões não suportadas, campos desconhecidos, chaves JSON
duplicadas, tipos inválidos, coordenadas ou componentes duplicados e `null`
falham fechados.

A igualdade exata de `formattedValue` para `CELL_DISPLAY` foi retida e a
semântica de aceitação não mudou. A4 e J1 continuam assertions de display; não
há expectativa de visibilidade para linha/coluna. Valores authored e formatos
de M1/N1 permanecem `UNSPECIFIED`. K1, L1, O1 e P1 seguem os contratos
explícitos do spec. O1 same-formula rewrite permanece
`STILL_REQUIRES_CONTROLLED_REAL_TEST`; o driver repo-local V2 que o poderá
executar está implementado offline, mas nenhuma validação real ocorreu. P1
permanece sem valor ou fórmula authored e nunca é alvo de escrita direta.

### Preflight e VERIFY_ONLY

O procedimento anterior de preflight exigia evidência de locale
verificado para o ID recebido em runtime, proveniente de
`SHEETS_SPREADSHEET_PROPERTIES` e vinculado àquele arquivo. Sem prova, a
classificação histórica é `FIXTURE_LOCALE_UNVERIFIED`; a comparação com `en_US`
está **SUPERSEDED**. O preflight não altera locale e não inicia reparo. O reader
de produção continua locale-agnostic.

O modo `VERIFY_ONLY` é um procedimento anterior, não parte do próximo gate.
Quando autorizado em fase própria, recebe o ID exato como entrada runtime,
valida a identidade por metadata exact-ID e lê somente `A1:P1`, `A4`,
`A6:B6` e `Z900`. Não existe interface de Drive search/list nem capacidade de
escrita no protocolo de leitura. Metadata preflight/postflight e a avaliação
retornam somente classificações e estados seguros, sem ID ou valores observados.
O CLI do helper canônico de contrato/setup expõe o plano; ele não é o driver de
leitura Google. O driver controlado V2 descrito abaixo é separado, exige seu
próprio modo explícito e não foi executado contra Google nesta entrega.

### APPLY_EXPLICIT_REPAIR

`APPLY_EXPLICIT_REPAIR` é um modo separado histórico: exige seleção explícita do modo,
identificador do gate de autorização e confirmação explícita em runtime. O
driver mantém a leitura pré-escrita em memória, produz plano determinístico e
limita o campo de escrita a `userEnteredValue` de K1/L1, preservando os formatos
canônicos NUMBER `0.00` e PERCENT `0.0%`. Após a escrita, verifica os resultados
focados. Se uma pós-condição falhar, tenta uma única restauração dos valores
authored salvos e confirma o estado focado; falha de restauração termina como
`ROLLBACK_UNCONFIRMED`, sem retry. O plano nunca inclui P1. O1 não é uma ação
executável deste helper; sua operação dedicada é implementada somente no
driver controlado V2 descrito abaixo. A recomendação antiga para o gate
`WORKSPACE-CONTENT-GSHEETS-DWD-SPREADSHEETS-SCOPE-VERIFY-AND-PROVISION-V1` está
**SUPERSEDED** como próximo passo. O próximo gate congelado é o diagnóstico
regional metadata-only; qualquer mudança administrativa exige solicitação e
execução manual pelo usuário. Locale divergente não será reparado pelo
diagnóstico.

O contrato de driver é injetado por `VerifyOnlyReader` e
`ExplicitRepairDriver`; não abre cliente Google, ADC, OAuth ou rede por conta
própria. O ID de arquivo permanece argumento runtime e não deve ser salvo em
spec, log, captura ou output.

Nota para a Phase C: o padrão repository-wide `*.json` do `.gitignore` também
ignora o spec canônico. A revisão futura deverá inspecionar seu conteúdo para
privacidade e decidir/documentar o tracking intencional antes de um checkpoint.
Não há instrução vigente para stage/force-add: checkpoint exige revisão e gate
separados.

Verificações offline:

```powershell
uv run python -B -m pytest -q -p no:cacheprovider tests\test_gsheets_validation_v1_fixture_contract.py
uv run python -B validation\gworkspace_rerun4_harness_safe.py --self-test
```

O plano anterior que recomendava teste real imediato de restauração de spill
O1/P1 está **SUPERSEDED**. O1/P1 só entram depois do diagnóstico regional, da
rebase e de uma leitura read-only específica; qualquer reparo é posterior e
separadamente autorizado.

## Histórico — O1/P1 spill restoration controlled driver

Este driver é uma ferramenta interna de validação, não uma capacidade do MVP.
Seu uso real está **QUARANTINED** e não é parte do próximo gate. Se uma escrita
futura se tornar necessária, exige
`REGIONAL_REQUALIFICATION_REQUIRED_BEFORE_FUTURE_REAL_WRITE`. Nenhuma operação
O1/P1 está autorizada pelo freeze documental.

O MCP público e o adapter Sheets público continuam somente leitura. O profile
interno fixo `drive.readonly + spreadsheets` e o builder privado auditado são
reutilizados pelo driver abaixo, mas continuam fora do bootstrap, runtime e
catálogo MCP. O catálogo é 24 tools, Write 0. Um registro anterior deste
runbook reporta `DWD_SPREADSHEETS_SCOPE_READY`; outro documento mantinha o scope
como não confirmado. Essa divergência foi reconciliada pela evidência de
readiness e reparo registrada em `docs/05_CHANGE_HISTORY.md`.

O driver repo-local e o transporte de validação estão implementados em:

- `validation/fixtures/run_gsheets_spill_restoration_controlled_v1.py`
- `validation/fixtures/gsheets_controlled_write.py`

O driver deriva a raiz de seu próprio `__file__`, valida os marcadores e carrega
o spec pelo loader canônico antes de qualquer input operacional. O modo local
não lê Fixture ID, config, ADC ou rede; o modo execute valida o ID process-local
por SHA-256 antes da ponte config/auth. O transporte limita-se a metadata
Drive exact-ID, metadata do workbook, uma leitura O1:P1 antes/depois e uma
possível regravação O1 (`updateCells`, máscara `userEnteredValue`, orçamento de
uma tentativa). P1 nunca é alvo de escrita. Search/list, ranges arbitrários,
retries, polling e rollback não existem nessa interface.

Verificações offline recomendadas para o driver:

```powershell
uv run python -B validation\fixtures\run_gsheets_spill_restoration_controlled_v1.py --help
uv run python -B validation\fixtures\run_gsheets_spill_restoration_controlled_v1.py --local-preflight
uv run python -B -m pytest -q -p no:cacheprovider tests\test_gsheets_spill_restoration_controlled_driver.py
uv run python -B -m pytest -q -p no:cacheprovider tests\test_content_operational_auth.py
```

Esta implementação V2 executou somente testes com fakes/MockTransport. A
validação real final de Sheets foi concluída em 02/10/2026; o driver O1/P1
continua uma ferramenta privada de validação, sem exposição no MCP.

### Post-write failure gating V1 — PASS offline

Uma falha de `write_o1_once()` consome a única tentativa e encerra o driver
imediatamente como `G — WRITE_FAILURE`. O caminho não faz leitura O1:P1
pós-write, Drive postflight, retry ou rollback. O transporte atual sinaliza
falha por `ControlledTransportError`; seu contrato não define um resultado
explícito de falha nem uma resposta de write cujo conteúdo precise ser
interpretado.

Depois de uma escrita bem-sucedida, a verificação continua obrigatória: uma
leitura O1:P1 pós-write, um Drive postflight e classificação baseada na
evidência. Os caminhos existentes para `A — SAME_FORMULA_REWRITE_RESTORED_SPILL`,
`B — SAME_FORMULA_REWRITE_DID_NOT_RESTORE_SPILL` e
`D — O1_POSTWRITE_CONTRACT_VIOLATION` permanecem cobertos.

Comandos de regressão offline deste gate:

```powershell
uv run python -B -m pytest -q -p no:cacheprovider tests\test_gsheets_spill_restoration_controlled_driver.py
uv run python -B -m pytest -q -p no:cacheprovider tests\test_content_operational_auth.py
uv run python -B -m pytest -q -p no:cacheprovider tests\test_gsheets_validation_v1_fixture_contract.py
uv run python -B validation\gworkspace_rerun4_harness_safe.py --self-test
uv run python -B -m pytest -q -p no:cacheprovider tests\test_google_sheets_content.py
uv run python -B -m pytest -q -p no:cacheprovider tests\test_content_public_file_ref.py tests\test_content_operational_auth.py tests\test_content_reading_substrate.py tests\test_google_docs_content.py tests\test_google_sheets_content.py
uv run python -B -m pytest -q -p no:cacheprovider
```

O `--local-preflight` pode ser executado da raiz ou de cwd externo usando o
caminho explícito do driver e o projeto `uv` do repositório. Esses modos não
leem `GSHEETS_VALIDATION_V1_FILE_ID`, config, ADC ou rede.

### Drive preflight request contract V1 — PASS offline

O Drive preflight controlado usa somente `GET drive/v3/files/{fileId}` pelo ID
exato recebido depois do identity guard. A projeção é exatamente
`id,mimeType,trashed,modifiedTime`, e o único parâmetro adicional é
`supportsAllDrives=true`. Não há `q`, `corpora`, `driveId`,
`includeItemsFromAllDrives` nem operação de busca/listagem. O transporte mantém
host e método fechados, timeout finito, redirects desativados, corpo de resposta
limitado, sem retry e sem logging de request/resposta.

O transporte compara o `id` retornado com o ID solicitado dentro da boundary e
entrega apenas `id_present` e `id_matches_requested_exact_id`; o valor do ID
nunca entra no DTO ou no resultado seguro. A passagem ao Sheets exige ID
presente e correspondente, MIME presente e Google Sheets, `trashed` presente e
`false`, e `modifiedTime` não vazio, ISO 8601 parseável e com timezone. Campo
ausente, incorreto ou inválido encerra fail-closed antes da metadata Sheets.
O timestamp é mantido somente em memória para a comparação pós-write e não é
reportado.

O diagnóstico real anterior parou durante inspeção do contrato local e enviou
zero requests HTTP Drive; não observou resposta nem defeito Google. O repair e
os testes usam somente fakes/`httpx.MockTransport`; não acessam Google,
autenticação, rede, gcloud ou a fixture.

Regressão offline do repair:

```powershell
uv run python -B -m pytest -q -p no:cacheprovider tests\test_gsheets_spill_restoration_controlled_driver.py
uv run python -B -m pytest -q -p no:cacheprovider tests\test_content_operational_auth.py
uv run python -B -m pytest -q -p no:cacheprovider tests\test_gsheets_validation_v1_fixture_contract.py
uv run python -B validation\gworkspace_rerun4_harness_safe.py --self-test
uv run python -B -m pytest -q -p no:cacheprovider tests\test_google_sheets_content.py
uv run python -B -m pytest -q -p no:cacheprovider tests\test_content_public_file_ref.py tests\test_content_operational_auth.py tests\test_content_reading_substrate.py tests\test_google_docs_content.py tests\test_google_sheets_content.py
uv run python -B -m pytest -q -p no:cacheprovider
```

Registro histórico: o ponteiro para
`WORKSPACE-CONTENT-GSHEETS-DRIVE-PREFLIGHT-EVIDENCE-DIAGNOSTIC-V1-RETRY-1` e a
recomendação então registrada para
`WORKSPACE-CONTENT-GSHEETS-PENDING-DISPLAY-HARNESS-CONTRACT-ARCHITECTURE-OFFLINE-V1`
foram superados pelas etapas posteriores; não são instruções atuais. Consulte
`docs/04_PHASE_STATUS.md` para o estado durável.

### Entrada process-local de ID para um futuro gate real autorizado

O procedimento abaixo é somente um padrão histórico para um gate futuro que
exija o driver O1/P1; não faz parte do próximo gate e não foi executado neste
trabalho. Não use Fixture ID nesta fase documental.
Execute a partir da raiz do repositório, digite o ID no prompt mascarado e não
inclua o valor no comando Python/Codex, em argumento CLI, arquivo ou ambiente
User/Machine:

```powershell
$secureId = Read-Host -Prompt 'Fixture ID' -AsSecureString
$idBuffer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureId)
try {
    $env:GSHEETS_VALIDATION_V1_FILE_ID = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($idBuffer)
    uv run python -B validation\fixtures\run_gsheets_spill_restoration_controlled_v1.py --execute-controlled-test
}
finally {
    Remove-Item Env:GSHEETS_VALIDATION_V1_FILE_ID -ErrorAction SilentlyContinue
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($idBuffer)
    $secureId.Dispose()
}
```

O valor fica somente na variável de processo herdada pelo filho e é limpo ao
terminar; o driver também o remove do próprio `os.environ` assim que o ingere.
Não use `setx` nem grave esse valor em config.toml, spec ou script.
