# Configuração Google Cloud e Google Workspace Admin

## Estado confirmado do projeto

| Item | Estado documentado |
| --- | --- |
| Projeto Google Cloud | `codex-workspace-admin` |
| Service Account | `codex-workspace@codex-workspace-admin.iam.gserviceaccount.com` |
| Modelo de autenticação | ADC local + IAM `signJwt` + DWD + OAuth 2.0 |
| Chave privada de Service Account | Não utilizada nem permitida |
| API de recursos Workspace | Admin SDK Directory API (`admin.googleapis.com`) |
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

Os registros enviados pelo usuário confirmam que o scope ChromeOS foi incluído
em 10/09/2026 depois de constatar que não estava presente, e que o scope de
gerenciamento de funções já existia. Os scopes de usuário, grupos e OUs não
terminam em `.readonly`, embora as ferramentas atuais apenas consultem dados;
isso é uma dívida de menor privilégio a ser avaliada cuidadosamente, sem
quebrar o comportamento existente.

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

## O que não fazer

- Não criar/download de key JSON, mesmo para "facilitar" testes.
- Não pôr tokens, JWTs, cabeçalhos HTTP ou ADC em `.env`, documentação, testes
  ou commits.
- Não autorizar scopes de Calendar, Reports, Drive ou Gmail enquanto a
  respectiva ferramenta não estiver especificada, implementada e revisada.
- Não permitir que a chamada MCP escolha livremente quem será impersonado.
