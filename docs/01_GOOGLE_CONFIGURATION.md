# Configuração Google Cloud e Google Workspace Admin

## Estado confirmado do projeto

| Item | Estado documentado |
| --- | --- |
| Projeto Google Cloud | `codex-workspace-admin` |
| Service Account | `codex-workspace@codex-workspace-admin.iam.gserviceaccount.com` |
| Modelo de autenticação | ADC local + IAM `signJwt` + DWD + OAuth 2.0 |
| Chave privada de Service Account | Não utilizada nem permitida |
| API de recursos Workspace | Admin SDK Directory API (`admin.googleapis.com`), incluindo `resources.buildings`, `resources.calendars` e `resources.features` |
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
  -> chamada Admin SDK Directory API
```

O cache renova o token antes da margem de cinco minutos e não persiste nada em
disco. Se a ADC local expirar ou for revogada, o diagnóstico pode exigir
`gcloud auth application-default login`; isso é diferente da renovação normal
do token Workspace.

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

Os scopes que o código atual solicita e que devem estar autorizados para esse
Client ID são:

| Recurso atual | Scope solicitado pelo código |
| --- | --- |
| Usuários | `https://www.googleapis.com/auth/admin.directory.user` |
| Grupos | `https://www.googleapis.com/auth/admin.directory.group` |
| Membros de grupos | `https://www.googleapis.com/auth/admin.directory.group.member` |
| Unidades organizacionais | `https://www.googleapis.com/auth/admin.directory.orgunit` |
| Dispositivos móveis | `https://www.googleapis.com/auth/admin.directory.device.mobile.readonly` |
| Dispositivos ChromeOS | `https://www.googleapis.com/auth/admin.directory.device.chromeos.readonly` |
| Funções e atribuições administrativas | `https://www.googleapis.com/auth/admin.directory.rolemanagement.readonly` |
| Domínios e aliases | `https://www.googleapis.com/auth/admin.directory.domain.readonly` |
| Buildings, Resources / Salas e Features (recursos corporativos) | `https://www.googleapis.com/auth/admin.directory.resource.calendar.readonly` — DWD confirmada administrativamente; validação MCP real concluída para as três coleções em 11/09/2026; Buildings exigiu reautenticação manual prévia da ADC |

Os registros enviados pelo usuário confirmam que o scope ChromeOS foi incluído
em 10/09/2026 depois de constatar que não estava presente, e que o scope de
gerenciamento de funções já existia. Os scopes de usuário, grupos e OUs não
terminam em `.readonly`, embora as ferramentas atuais apenas consultem dados;
isso é uma dívida de menor privilégio a ser avaliada cuidadosamente, sem
quebrar o comportamento existente.

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
- [Calendar resources: `resources.calendars.list`](https://developers.google.com/workspace/admin/directory/reference/rest/v1/resources.calendars/list)
- [Calendar resource features: `resources.features.list`](https://developers.google.com/workspace/admin/directory/reference/rest/v1/resources.features/list)

## O que não fazer

- Não criar/download de key JSON, mesmo para "facilitar" testes.
- Não pôr tokens, JWTs, cabeçalhos HTTP ou ADC em `.env`, documentação, testes
  ou commits.
- Não autorizar scopes da Google Calendar API, Reports, Drive ou Gmail por
  conveniência. Buildings, Resources / Salas e Features usam somente o scope
  readonly da Directory API documentado acima e sua alteração de DWD continua
  sujeita a autorização explícita.
- Não permitir que a chamada MCP escolha livremente quem será impersonado.
