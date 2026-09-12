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
reautenticação ADC continua manual pelo usuário.

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
