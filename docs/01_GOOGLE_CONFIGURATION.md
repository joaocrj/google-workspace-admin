# Configuração Google Cloud e Google Workspace Admin

## Estado confirmado do projeto

| Item | Estado documentado |
| --- | --- |
| Projeto Google Cloud | `codex-workspace-admin` |
| Service Account | `codex-workspace@codex-workspace-admin.iam.gserviceaccount.com` |
| Modelo de autenticação | ADC local + IAM `signJwt` + DWD + OAuth 2.0 |
| Chave privada de Service Account | Não utilizada nem permitida |
| APIs de recursos Workspace | Admin SDK Directory API e Reports API (`admin.googleapis.com`), incluindo recursos corporativos de Calendar e Admin Audit |
| Assinatura JWT | Service Account Credentials API (`iamcredentials.googleapis.com`) |
| Token Workspace | Curta duração, cache somente em memória |
| Sujeito delegado | Controlado por `config.py`; não é parâmetro de ferramenta MCP |

O código é deliberadamente **keyless**. A chave gerenciada pelo Google assina o
JWT via `projects.serviceAccounts.signJwt`; nenhuma chave privada passa pela
máquina local ou pelo Git.

## Fluxo de autenticação que já foi implementado

```text
ADC do operador local
  -> token cloud-platform para IAM Credentials
  -> POST ...serviceAccounts/{service-account}:signJwt
  -> JWT com iss, sub, scopes, aud, iat e exp
  -> POST oauth2.googleapis.com/token (JWT bearer)
  -> token do Workspace em memória, por sujeito + conjunto normalizado de scopes
  -> chamada à API Admin SDK aplicável (Directory ou Reports)
```

O cache renova o token antes da margem de cinco minutos e não persiste nada em
disco. Se a ADC local expirar ou for revogada, a reautenticação local pode
exigir `gcloud auth application-default login`. Isso é reautenticação da ADC
local, não renovação manual do token DWD e não exige chave JSON de Service
Account.

## Processo realizado no Google Cloud / Google Developer

O histórico do projeto confirma que a autenticação, `signJwt`, DWD, a troca de
token e as chamadas Directory foram validadas em 03/09/2026. A configuração que
deve ser preservada é:

1. No projeto `codex-workspace-admin`, a Service Account acima possui DWD
   habilitada. Não crie uma chave JSON para ela.
2. A API **Admin SDK API** está habilitada para atender o serviço
   `admin.googleapis.com`.
3. A API **Service Account Credentials API** está habilitada para atender
   `iamcredentials.googleapis.com` e `signJwt`.
4. A identidade local usada pela ADC tem, na Service Account, permissão
   `iam.serviceAccounts.signJwt`; o papel normalmente associado é
   `roles/iam.serviceAccountTokenCreator`. A concessão deve ficar restrita à
   Service Account necessária.
5. A ADC é obtida localmente. Não exportar seu arquivo, nem copiá-lo para um
   servidor remoto. Para implantação futura, usar Workload Identity ou uma
   identidade de workload equivalente.

O repositório não registra o principal que recebeu a permissão IAM nem o Client
ID numérico da Service Account. Isso é proposital: consulte-os no Console antes
de uma alteração; não adivinhe ou acrescente valores de exemplo.

## Processo realizado no Google Admin Console

Uma conta Super Admin autorizou a Service Account para Domain-Wide Delegation.
O caminho administrativo é **Security > Access and data control > API controls
> Manage Domain Wide Delegation**. A entrada deve usar o **Client ID numérico**
da Service Account, recuperado no Google Cloud Console em *IAM & Admin > Service
Accounts > [conta] > Advanced settings* — não use o e-mail da Service Account
no campo de Client ID.

Os scopes abaixo são o inventário DWD operacional atualmente documentado para
esse Client ID. Os quatro scopes Directory migrados usam os targets
`.readonly`, confirmados manualmente pelo usuário e validados individualmente.
Os valores amplos anteriores permanecem somente no histórico de marcos.

| Recurso atual | Scope solicitado pelo código |
| --- | --- |
| Usuários | `https://www.googleapis.com/auth/admin.directory.user.readonly` |
| Grupos | `https://www.googleapis.com/auth/admin.directory.group.readonly` |
| Membros de grupos | `https://www.googleapis.com/auth/admin.directory.group.member.readonly` |
| Unidades organizacionais | `https://www.googleapis.com/auth/admin.directory.orgunit.readonly` |
| Dispositivos móveis | `https://www.googleapis.com/auth/admin.directory.device.mobile.readonly` |
| Dispositivos ChromeOS | `https://www.googleapis.com/auth/admin.directory.device.chromeos.readonly` |
| Funções e atribuições administrativas | `https://www.googleapis.com/auth/admin.directory.rolemanagement.readonly` |
| Domínios e aliases | `https://www.googleapis.com/auth/admin.directory.domain.readonly` |
| Buildings, Resources / Salas e Features (recursos corporativos) | `https://www.googleapis.com/auth/admin.directory.resource.calendar.readonly` — DWD confirmada administrativamente; validação MCP real concluída para as três coleções em 11/09/2026; Buildings exigiu reautenticação manual prévia da ADC |
| Admin Audit (Reports API) | `https://www.googleapis.com/auth/admin.reports.audit.readonly` — DWD confirmada manualmente; sujeito Superadministrador; REAL VALIDATION MCP concluída em 11/09/2026 com launcher Python da `.venv`, 1 Activity e próxima página presente; checkpoint Git concluído |
| Login Audit (Reports API) | `https://www.googleapis.com/auth/admin.reports.audit.readonly` — reutiliza o scope já presente e confirmado manualmente para Reports; REAL VALIDATION MCP concluída em 11/09/2026 com uma chamada limitada, 1 Activity e próxima página presente; nenhuma alteração administrativa nova |
| User Usage (Reports API) | `https://www.googleapis.com/auth/admin.reports.usage.readonly` — método `UserUsageReport.get`; DWD e scopes não foram alterados; REAL VALIDATION executada com sucesso em `2026-09-12`; data do relatório solicitado: `date=2026-09-10`, `max_results=1`, `parameters=accounts:used_quota_in_percentage`, `user_key=all`, `usageReports=1`, próxima página presente, warnings presentes (1), sem retry ou paginação adicional |
| Customer Usage (Reports API) | `https://www.googleapis.com/auth/admin.reports.usage.readonly` — método `CustomerUsageReports.get`; reutiliza DWD e scope já autorizado; IMPLEMENT concluído; REAL VALIDATION V9 concluída; checkpoint concluído; nenhuma alteração administrativa nova |

### CODE TARGET e migração DWD manual

Na camada READ, os alvos de código desta consolidação são:

| Área | CODE TARGET | DWD MANUAL MIGRATION |
| --- | --- | --- |
| users/list e users/get | `admin.directory.user.readonly` | COMPLETE — confirmação manual |
| groups/list | `admin.directory.group.readonly` | COMPLETE — confirmação manual |
| group members/list | `admin.directory.group.member.readonly` | COMPLETE — confirmação manual |
| orgunits/list | `admin.directory.orgunit.readonly` | COMPLETE — confirmação manual |

**DWD STATUS: MIGRATION CONFIRMED MANUALLY; REAL VALIDATION PASSED.** O
usuário substituiu manualmente, no Admin Console, os quatro scopes antigos
pelos targets acima e confirmou a propagação. Este repositório não altera DWD,
Admin Console, IAM, APIs ou Google Cloud automaticamente.

Os registros enviados pelo usuário confirmam que o scope ChromeOS foi incluído
em 10/09/2026 depois de constatar que não estava presente, e que o scope de
gerenciamento de funções já existia. O código READ e a DWD atual apontam users,
groups, group members e orgunits para os quatro targets `.readonly` acima.
Os scopes amplos anteriores não são estado operacional atual.

Os serializers de Mobile e ChromeOS preservam deliberadamente IDs de
dispositivo, serial, IMEI/MEID, MAC, localização e usuário anotados porque são
campos necessários ao inventário administrativo; a exposição é intencional e
deve ser tratada como potencialmente sensível pelo consumidor. Parâmetros de
Admin Audit também podem conter dados administrativos potencialmente sensíveis
e não devem ser redistribuídos sem necessidade.

`workspace_buildings_list` usa exclusivamente o scope readonly de recursos de
Calendar acima, porque Buildings é a coleção `resources.buildings` da **Admin
SDK Directory API**, não da Google Calendar API. Em 11/09/2026, um
Superadministrador confirmou a inclusão desse scope na DWD e que o sujeito
delegado possui privilégio abrangente para **Calendar > View Resources**. Após
o usuário reautenticar manualmente a ADC, a chamada MCP real limitada a uma
única página foi concluída com sucesso, retornando zero Buildings e sem página
seguinte. Não altere DWD, IAM ou scopes automaticamente; qualquer mudança
administrativa futura continua dependente de solicitação e execução manual do
usuário.

`workspace_calendar_resources_list` usa o mesmo scope, porque Resources / Salas
é a coleção irmã `resources.calendars` da mesma Admin SDK Directory API. Não há
scope, API, IAM, DWD ou privilégio adicional previsto para a implementação
local. Em 11/09/2026, um processo MCP `stdio` novo validou a cadeia keyless
com uma única consulta limitada a `max_results=1`: a chamada foi bem-sucedida,
retornou zero Resources / Salas e não indicou página seguinte. Nenhuma
credencial, token de paginação ou dado de recurso foi registrado.

`workspace_calendar_features_list` usa esse mesmo scope readonly, pois
Features é a coleção irmã `resources.features` da Admin SDK Directory API. A
documentação oficial autoriza `resources.features.list` com esse scope; a
implementação local está concluída, sem necessidade de API, IAM, DWD, scope ou
privilégio adicional. Em 11/09/2026, após confirmar a capacidade da ADC sem
registrar material de autenticação, um processo MCP `stdio` novo validou a
cadeia keyless com uma única chamada limitada a `max_results=1`: a chamada foi
bem-sucedida, retornou zero Features e não indicou página seguinte. Nenhuma
alteração administrativa, credencial, token de paginação ou dado de Feature foi
registrado.

`workspace_admin_audit_list` usa exclusivamente
`https://www.googleapis.com/auth/admin.reports.audit.readonly` para a Reports
API, com `applicationName=admin` fixo. O usuário confirmou manualmente a DWD
desse scope e o sujeito delegado como Superadministrador. A REAL VALIDATION
MCP foi executada uma única vez pelo launcher Python da `.venv`, retornando
1 Activity e indicando próxima página; nenhum conteúdo de auditoria foi
registrado. Tentativas anteriores em `codexsandboxoffline` falharam por
restrições locais de socket/cache ou por um `stderr` incompatível do harness,
sem evidência de falha no servidor, DWD ou Reports API. Não há nova API, IAM ou
Service Account prevista, e nenhuma alteração administrativa foi realizada.

`workspace_login_audit_list` usará o mesmo scope readonly da Reports API, com
`applicationName=login` fixo no endpoint
`/admin/reports/v1/activity/users/{userKey}/applications/login`. A implementação
local limita páginas a 1–100 (padrão 25), preserva `nextPageToken`, não envia
`customerId` nem `includeSensitiveData`, não percorre páginas e não cria
retries. O scope já está presente na configuração documentada por causa de
Admin Audit. Em 11/09/2026, a REAL VALIDATION específica de Login Audit foi
concluída pelo MCP carregado pelo host, com uma única chamada limitada a
`max_results=1`, 1 Activity e `next_page_token` presente. Nenhum conteúdo da
Activity, dado pessoal, credencial ou token foi registrado; a validação não
afirma cobertura de todos os tipos de eventos Login. Nenhuma alteração de DWD,
IAM, API, Service Account, privilégio ou Google Admin foi realizada.

`workspace_drive_audit_list` usa a Reports API, com
`applicationName=drive` fixo no endpoint
`/admin/reports/v1/activity/users/{userKey}/applications/drive`. Ela reutiliza
exclusivamente o scope já autorizado
`https://www.googleapis.com/auth/admin.reports.audit.readonly`; não requer novo
scope, nova API, alteração de DWD, IAM, Service Account, sujeito ou privilégio
delegado. A implementação mantém páginas de 1–100 registros, padrão 25,
`page_token` explícito, timeout de 30 segundos, uma requisição por chamada,
sem retry ou auto-paginação. O contrato não envia `customerId`, filtros novos
de recursos/rede/status/agentes/dispositivos nem `includeSensitiveData`.

Drive Audit não acessa conteúdo de arquivos e não usa Drive Activity API v2,
Drive `files.get`, Docs API, Sheets API, Slides API ou exportação. O serializer
é específico e allowlistado: mantém timestamp, qualificador, evento, ator/IP e
IDs opacos necessários à correlação, mas omite títulos, proprietários,
destinatários, queries, conteúdo, `sensitiveParameters`, `resourceDetails`,
`networkInfo`, `userDeviceInfo`, aplicações OAuth, dados agentic e estruturas
desconhecidas. A documentação operacional preserva a nuance entre a janela do
relatório descrita como até 180 dias e a retenção geral de auditoria descrita
como seis meses; essa diferença não vira uma regra artificial local. Em
11/09/2026, a REAL VALIDATION do Drive Audit foi concluída exclusivamente pelo
MCP original carregado pelo host, com exatamente uma chamada
`workspace_drive_audit_list(max_results=1)`: sucesso, 1 Activity e
`next_page_token` presente. A cadeia keyless foi validada até a Reports API;
nenhum conteúdo real de Activity foi persistido. O checkpoint Git desta entrega
é concluído com o commit autorizado após as verificações finais; qualquer
mudança administrativa continua fora do escopo do agente.

`workspace_user_usage_get` usa exclusivamente
`https://www.googleapis.com/auth/admin.reports.usage.readonly` para o método
`UserUsageReport.get`, no endpoint
`/admin/reports/v1/usage/users/{userKey}/dates/{date}`. A implementação local
não usa `activities.list`, Drive Activity API, `customerUsageReports` nem envia
`customerId`. A DWD e os scopes não foram alterados para essa validação. A
REAL VALIDATION foi executada em `2026-09-12`, com uma única chamada para a
data do relatório solicitado `date=2026-09-10`, `max_results=1`,
`parameters=accounts:used_quota_in_percentage` e `user_key=all`: sucesso,
`usageReports=1`, `next_page_token` presente, `warnings_present=true` e
`warnings_count=1`, sem retry ou paginação adicional. Nenhum conteúdo de uso,
credencial ou token foi registrado.

`workspace_customer_usage_get` usa exclusivamente
`https://www.googleapis.com/auth/admin.reports.usage.readonly` para o método
`CustomerUsageReports.get`, no endpoint
`/admin/reports/v1/usage/dates/{date}`. O contrato expõe somente `date`,
`parameters` obrigatório e `page_token` opcional; não envia `customerId`,
`maxResults`, `userKey`, `filters` ou `orgUnitID`.

`parameters` aceita somente o CSV explícito das dez métricas integer
allowlisted de Accounts. O `page_token` é encaminhado como `pageToken`, uma
única página é processada por chamada, `nextPageToken` é normalizado como
`next_page_token`, não há retry automático e o timeout é de 30 segundos.
`date` representa exclusivamente a data solicitada do relatório, nunca a data
de execução ou validação. A REAL VALIDATION V9 de Customer Usage foi concluída
anteriormente com uma única chamada limitada; esta IMPLEMENT não executa nova
validação real.

Ao alterar scopes, um Super Admin deve revisar toda a lista, aplicar apenas a
diferença necessária, aguardar a propagação e validar uma operação de leitura.
Se a organização usa aprovação por múltiplas partes, a alteração também requer
o segundo aprovador. Alterar ou apagar DWD interrompe imediatamente as
ferramentas dependentes e exige autorização explícita do usuário.

## Referências oficiais

- [Delegação em todo o domínio — Admin Console](https://knowledge.workspace.google.com/admin/apps/control-api-access-with-domain-wide-delegation)
- [Service accounts e DWD](https://developers.google.com/identity/protocols/oauth2/service-account)
- [Habilitar APIs do Google Workspace](https://developers.google.com/workspace/guides/enable-apis)
- [Permissões IAM para `signJwt`](https://docs.cloud.google.com/iam/docs/service-account-permissions)
- [Admin SDK Directory API](https://developers.google.com/workspace/admin/directory/reference/rest)
- [Admin SDK Reports API: `activities.list`](https://developers.google.com/workspace/admin/reports/reference/rest/v1/activities/list)
- [Admin Activity Report](https://developers.google.com/workspace/admin/reports/v1/guides/manage-audit-admin)
- [Login Activity Report](https://developers.google.com/workspace/admin/reports/v1/guides/manage-audit-login)
- [Login Audit Activity Events](https://developers.google.com/workspace/admin/reports/v1/appendix/activity/login)
- [User Usage Report — `userUsageReport.get`](https://developers.google.com/workspace/admin/reports/reference/rest/v1/userUsageReport/get)
- [User Usage Parameters](https://developers.google.com/workspace/admin/reports/v1/appendix/usage/user)
- [Accounts User Usage Parameters](https://developers.google.com/workspace/admin/reports/v1/appendix/usage/user/accounts)
- [Google Chat User Usage Parameters](https://developers.google.com/workspace/admin/reports/v1/appendix/usage/user/chat)
- [Classroom User Usage Parameters](https://developers.google.com/workspace/admin/reports/v1/appendix/usage/user/classroom)
- [Gmail User Usage Parameters](https://developers.google.com/workspace/admin/reports/v1/appendix/usage/user/gmail)
- [Google Docs User Metrics](https://developers.google.com/workspace/admin/reports/v1/appendix/usage/user/docs)
- [Calendar resources: `resources.calendars.list`](https://developers.google.com/workspace/admin/directory/reference/rest/v1/resources.calendars/list)
- [Calendar resource features: `resources.features.list`](https://developers.google.com/workspace/admin/directory/reference/rest/v1/resources.features/list)

## O que não fazer

- Não criar/download de key JSON, mesmo para "facilitar" testes.
- Não pôr tokens, JWTs, cabeçalhos HTTP ou ADC em `.env`, documentação, testes
  ou commits.
- Não autorizar scopes da Google Calendar API, Reports, Drive ou Gmail por
  conveniência. Os recursos corporativos de Calendar usam somente o scope
  readonly da Directory API documentado acima; o scope mínimo de Admin Audit é
  documentado exclusivamente para a implementação local e já foi confirmado
  manualmente para esta validação. Qualquer alteração futura na DWD continua
  sujeita a solicitação prévia e execução manual do usuário.
- Não permitir que a chamada MCP escolha livremente quem será impersonado.

## Fase 1.5 — Foundation local

A Foundation Content Implement V1 adiciona somente contratos locais e
allowlists internas para uma futura Content Layer. Ela **não** adiciona
scopes ao inventário DWD operacional, não cria Service Account, não habilita
APIs e não altera IAM, ADC ou Admin Console.

Os profiles read-only verificados para uso futuro são mantidos no código como
contratos fechados: Drive discovery, Drive metadata, Docs, Sheets, Slides,
Gmail metadata e Gmail content. A presença desses valores no registry local
não significa que estejam autorizados no Google Cloud/DWD.

## Fase 1.5 — Foundation Remediation Implement V1

A remediação permanece exclusivamente local. O `ContentAuthBroker` aceita
somente authorities emitidas pelo registry/resolver — profile handle, subject
handle e capability context — e não objetos de configuração ou argumentos MCP.
O registry é populado por configuração administrativa de startup e não por
argumentos MCP. Nenhum token, JWT, chamada DWD, mudança de scope, Service
Account Content ou alteração de Admin Console foi executado.

Os limites `DEFAULT_PAGE_SIZE`, `CONTENT_HARD_CAP` e
`MAX_ITEMS_PER_INVOCATION` são políticas internas de segurança. Eles não
substituem os limites oficiais de API, mantidos separadamente como
`API_MAX_PAGE_SIZE`. O transport de Content usa endpoints fixos, client de
produção controlado, redirects desativados e client mockável somente em testes.

O estado externo continua pendente: Content Research Service Account/DWD não
foi criado, nenhuma API Content foi habilitada ou validada funcionalmente e a
validação real RV1 de Shared Drive não foi executada.

## Fase 1.5 — Foundation Remediation Implement V2

A remediação V2 tornou obrigatória a cadeia local
`registered profile handle → authorized subject handle → broker-issued
operation context → typed result`. `ContentAuthProfile` e `WorkspaceSubject`
continuam sendo objetos de dados, não authorities; provenance é verificada por
membership/issuer em runtime. O transport não aceita client arbitrário pelo
construtor público, não expõe JSON genérico e mantém redirects desativados.

Foram adicionados ceilings absolutos de contexto, enforcement operacional de
`max_items`, retry conservador (400/401/403/404 nunca repetidos) e resultados
allowlistados para os três contratos Drive internos. Isso continua sendo
somente infraestrutura local: Content SA/DWD, scopes no Google Cloud, APIs e
validação funcional permanecem não executados.

## Fase 1.5 — Foundation Remediation Implement V3

A remediação V3 substitui a provenance baseada em atributos e coleções de
issuer por handles sem dados e membership fraca por identidade, mantida em
closures exclusivas de cada runtime. Profiles, subjects e contextos fabricados,
copiados ou emitidos por outro runtime não adquirem autoridade. Registry,
resolver, broker, normalização e HTTP adapter são montados no composition root
e não são parâmetros de uma operação Content.

`create_content_runtime()` não aceita configuração, Service Account, customer,
auditor, scopes, resolver, broker, transport ou client. Enquanto a futura
configuração Content Research não existir, o bootstrap de produção falha
localmente como não provisionado, antes de criar client ou executar HTTP. Os
testes substituem providers internos somente antes da montagem e usam
`httpx.MockTransport`; o runtime pronto não oferece setter/attach de client ou
de componentes.

Nada nesta arquitetura configura ou valida Google: Content Research Service
Account, DWD, scopes, APIs, privilégios, tokens e Drive RV1 continuam ausentes
e dependem de entrega manual futura expressamente autorizada. A arquitetura
histórica Read `ADC -> IAM signJwt -> DWD -> OAuth` não foi modificada.

## Fase 1.5 — Foundation Remediation Implement V4

A Remediation V4 reduziu a superfície local de composição: o único caminho
suportado para montar o runtime é o startup composition root. `ContentRuntime`
não aceita executor, broker, resolver, registry, adapter, client, profile ou
scope fornecido pelo caller. As operações Drive continuam fechadas, GET-only,
com host, path, fields e invariantes derivados internamente.

O threat model suportado cobre inputs MCP/runtime não confiáveis e a API
Content suportada. Execução arbitrária de Python dentro do processo,
monkeypatch/introspecção após comprometimento, debugger, manipulação de memória
e alteração deliberada de closures permanecem fora da boundary e não são
tratados como isolamento de processo.

Nenhum Content Service Account, DWD, scope, API, token ou validação Google foi
criado ou executado. A autenticação histórica Read `ADC -> IAM signJwt -> DWD
-> OAuth` permanece inalterada.

## Fase 1.5.1 — Shared Drive Discovery — IMPLEMENT V1 local

A implementação local adiciona somente as tools MCP
`workspace_drives_list` e `workspace_drive_get`. Elas permanecem lazy e
fail-closed: importar o servidor, enumerar o catálogo ou executar testes locais
não constrói ADC, não gera token e não faz chamada Google. Sem provisioning de
Content, uma invocação funcional falha localmente antes do HTTP.

O mapeamento fechado para a futura execução é:

| Tool | Método e endpoint fixos | Fields | Scope mínimo |
| --- | --- | --- | --- |
| `workspace_drives_list` | `GET https://www.googleapis.com/drive/v3/drives` | `nextPageToken,drives(id,name)` | `https://www.googleapis.com/auth/drive.readonly` |
| `workspace_drive_get` | `GET https://www.googleapis.com/drive/v3/drives/{driveId}` | `id,name` | `https://www.googleapis.com/auth/drive.readonly` |

O MCP aceita uma página por invocation, com `page_size` e `max_items` de 1 a
100, padrão 25 e 100 respectivamente; o tamanho efetivo é o mínimo dos dois.
`page_token` é opcional e opaco. Não há `q`, fields, endpoint, subject,
profile, scope ou paginação automática controlável pelo caller. O único
`next_page_token` devolvido é o token validado da resposta Google. O retorno é
allowlistado para IDs e nomes de Shared Drives; respostas, permissões,
capabilities, restrictions e headers brutos não são expostos.

`driveId` é o identificador operacional estável. Nome é somente atributo de
descoberta/display: nomes duplicados permanecem distintos no resultado, e não
há conversão ou seleção silenciosa por nome.

### Identidade Content Research — provisioning manual futuro

A identidade desta vertical deverá ser separada da Service Account usada pela
camada Read histórica. O estado abaixo é requisito futuro, não afirmação de
que a configuração exista:

- criar manualmente uma Content Research Service Account dedicada, sem chave
  JSON privada e sem registrar seu e-mail real no código;
- conceder manualmente à identidade ADC local, restrita àquela Service Account,
  `roles/iam.serviceAccountTokenCreator`/`iam.serviceAccounts.signJwt`;
- usar a mesma arquitetura keyless `ADC -> IAM signJwt -> DWD -> OAuth`, com
  DWD separada e somente o scope Drive readonly;
- definir por configuração administrativa fixa o customer, domínio, auditor e
  sujeito delegado; o sujeito não é parâmetro MCP nem entrada arbitrária;
- autorizar no Admin Console o Client ID numérico da Content Research Service
  Account com exatamente
  `https://www.googleapis.com/auth/drive.readonly`, aguardando a propagação;
- manter o token somente em RAM, com renovação bounded e sem persistir ADC,
  JWT, access token ou credencial.

`useDomainAdminAccess` é `false` por padrão. No modo ordinary, o profile
Content aprovado, o sujeito validado, a capability `DRIVE` e a capability
`SHARED_DRIVE_DISCOVERY` da operação devem estar satisfeitos. No modo
administrative, `true` é opt-in explícito e ainda exige todas essas políticas,
além de compatibilidade da operação; não concede autorização universal para
ler conteúdo.

### Gate manual anterior à REAL VALIDATION

| Console | Recurso/configuração exata | Por que | Quando | Verificação manual |
| --- | --- | --- | --- | --- |
| Google Cloud Console — APIs & Services | habilitar **Google Drive API** (`drive.googleapis.com`) no projeto autorizado | permitir `drives.list`/`drives.get` | antes de RV1 | conferir API como Enabled, sem executar uma tool ainda |
| Google Cloud Console — IAM & Admin > Service Accounts | criar/selecionar uma **Content Research Service Account** separada, sem JSON key | identidade dedicada e isolamento da Read SA | antes de configurar DWD | conferir conta e ausência de chaves privadas |
| Google Cloud Console — IAM | conceder `roles/iam.serviceAccountTokenCreator` somente ao principal ADC na Content SA | permitir `signJwt` keyless | antes de RV1 | revisar IAM policy e permissão `iam.serviceAccounts.signJwt` |
| Google Admin Console — Security > Access and data control > API controls > Manage Domain Wide Delegation | registrar o Client ID numérico da Content SA com somente `https://www.googleapis.com/auth/drive.readonly` | autorizar DWD separada para Drive | antes de RV1 e após propagação | confirmar Client ID, scope exato e estado propagado |
| Google Workspace Admin Console / política do domínio | confirmar sujeito delegado, customer/domain fixos e auditor configurado | resolver subject controlado e policy | antes de RV1 | validação administrativa do sujeito, status e domínio, sem aceitar input MCP |
| máquina local do operador | ADC válida para o principal que pode usar `signJwt` | autenticar somente a validação real | imediatamente antes de RV1, se necessário | operador pode executar `gcloud auth application-default print-access-token > $null`, sem imprimir o token |

Todas essas alterações são manuais do operador. Codex/MCP não cria Service
Account, não configura DWD, IAM, scopes, APIs ou Admin Console. A REAL
VALIDATION desta entrega não foi iniciada.

## Fase 1.5.1 — Operational Auth Binding — IMPLEMENT V1

O binding local agora lê somente estes identificadores não secretos, sob um
prefixo fechado, no momento da primeira operação Content:

| Variável | Obrigatória | Consumidor |
| --- | --- | --- |
| `GOOGLE_WORKSPACE_CONTENT_PROJECT_ID` | sim | validação do ADC e configuração Content |
| `GOOGLE_WORKSPACE_CONTENT_SERVICE_ACCOUNT` | sim | `ContentAuthProfile` e recurso fixo de `signJwt` |
| `GOOGLE_WORKSPACE_CONTENT_SUBJECT` | sim | `WorkspaceSubject` fixo e claims DWD |
| `GOOGLE_WORKSPACE_CONTENT_CUSTOMER_ID` | sim | profile e validação do subject |
| `GOOGLE_WORKSPACE_CONTENT_DOMAIN` | sim | política fixa de domínio |

O scope não é variável de ambiente. `DRIVE_DISCOVERY` resolve exclusivamente
para `https://www.googleapis.com/auth/drive.readonly`; Client ID DWD é uma
configuração administrativa e não é lido pelo runtime.

O bloco abaixo é somente a configuração process-only planejada para o operador
aplicar depois de obter o customer ID. Não o persista em `.env`, ambiente de
usuário ou `config.toml`, e substitua o placeholder antes de usar:

```powershell
$env:GOOGLE_WORKSPACE_CONTENT_PROJECT_ID = "codex-workspace-admin"
$env:GOOGLE_WORKSPACE_CONTENT_SERVICE_ACCOUNT = "codex-workspace-content@codex-workspace-admin.iam.gserviceaccount.com"
$env:GOOGLE_WORKSPACE_CONTENT_SUBJECT = "suporte.ti@cevalente.com.br"
$env:GOOGLE_WORKSPACE_CONTENT_CUSTOMER_ID = "<CUSTOMER_ID_A_FORNECER>"
$env:GOOGLE_WORKSPACE_CONTENT_DOMAIN = "cevalente.com.br"
```

O Content Research Service Account, a permissão IAM Token Creator e o DWD
`drive.readonly` foram **MANUALLY CONFIGURED**, conforme confirmação do
operador; esta implementação não os verifica. A ausência de qualquer variável,
inclusive `customer_id`, falha fechado antes de ADC, autenticação ou HTTP.

### Evidência operacional 1.5.1 — RV1, Diagnostic V1 e RV2

As cinco variáveis obrigatórias, incluindo `customer_id`, estão configuradas
na tabela `env` da instância MCP. Elas permanecem identificadores process-only
não secretos: não há variável de scope, Client ID DWD, token, JWT, chave privada
ou fallback `my_customer`.

O histórico de execução deve ser preservado: RV1 falhou no precheck de
configuração antes de qualquer operação Google (`functional operations = 0`)
porque o caminho direto Python/PowerShell não herdou o ambiente da instância
MCP. Diagnostic V1 confirmou o parse de `ContentConfig`, o provisioning do
profile e a construção do subject; a causa foi exclusivamente a boundary de
execução, não uma mudança de configuração Google.

RV2 executou exatamente uma chamada `workspace_drives_list` pelo MCP hospedado
com modo administrativo `false`. A cadeia `CONFIG → ADC → IAM signJwt → DWD
OAuth → Drive API` passou, retornou um Shared Drive e indicou token de próxima
página, sem retry, paginação adicional, mutação ou exposição de valor sensível.
Esta evidência valida a configuração operacional sem registrar IDs, nomes,
tokens, JWTs, cabeçalhos ou resposta bruta.

## Fase 1.5.2 — Drive File Inventory — IMPLEMENT V1 local

`workspace_drive_files_list` reutiliza integralmente o profile operacional
Content `DRIVE_DISCOVERY`, que resolve somente para
`https://www.googleapis.com/auth/drive.readonly`. A regra interna anterior de
`drive.files.list`, que apontava para `DRIVE_METADATA` /
`drive.metadata.readonly`, foi alinhada ao profile já provisionado; nenhum
scope, DWD, Service Account, IAM grant, API ou variável de ambiente foi criado
ou alterado.

O caminho permanece `ADC -> IAM signJwt -> Content Research SA -> DWD -> OAuth
-> Drive API`. As mesmas cinco variáveis process-only de 1.5.1 continuam sendo
o contrato completo de configuração. O inventário não expõe subject, profile,
scope ou admin mode. `useDomainAdminAccess` não é parâmetro de `files.list` e
permanece ausente da tool.

Esta entrega executou os testes locais com fakes e `httpx.MockTransport` e,
posteriormente, a RV2 autorizada pelo MCP hospedado: Google activity adicional
= 0 e ADC activity = 0. `REAL VALIDATION = PASS`; a execução limitou-se a obter um
`drive_id` pela tool existente e executar uma única página bounded do
inventário, sem registrar o ID. Essa RV2 foi concluída pelo MCP hospedado com
uma descoberta e uma página de inventário; não houve mudança externa de Google.

## Fase 1.5.3 — Content Reading Architecture & Safety — IMPLEMENT V1 local

PLAN V1 = **COMPLETE**; IMPLEMENT V1 = **COMPLETE** (substrate somente local).

Esta etapa adiciona somente primitives locais e imutáveis para futuros
readers: classes MIME fechadas, budgets de bytes/estrutura/tempo, snapshots de
inventário, chunks normalizados, provenance tipada, outcomes terminais,
preflight interno de `capabilities.canDownload`, protocolo de reader e policy
de conteúdo não executável.

Não foram adicionados readers concretos, endpoints Docs/Sheets/Slides/Drive
media, dependências de parser, variáveis de ambiente ou ferramentas MCP. O
profile permanece `DRIVE_DISCOVERY`, com o único scope
`https://www.googleapis.com/auth/drive.readonly`; nenhuma alteração de Google
Cloud, IAM, DWD, Service Account ou Admin Console ocorreu.

O contrato de cobertura exige exatamente um outcome terminal por arquivo
inventariado. Limite de primeira operação com continuação segura resulta em
`PARTIALLY_PROCESSED` mais token opaco; continuação impossível ou limite
absoluto resulta em `TOO_LARGE`. Conteúdo é tratado como dado não confiável e
nenhum macro, fórmula, script, hyperlink, entidade externa ou comando é
executado.

A revisão local V1 confirmou que não há reader concreto, endpoint, dependência,
scope ou alteração de configuração Google nesta etapa. REAL GOOGLE VALIDATION
= **NOT APPLICABLE / NOT EXECUTED**; FINAL REVIEW V1 = **COMPLETE**;
CHECKPOINT V1 = **COMPLETE**. Não há reader concreto nem nova configuração
Google nesta etapa; 1.5.4 aguarda autorização explícita.
