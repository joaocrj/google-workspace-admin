# Histórico de marcos

| Data | Commit | Marco |
| --- | --- | --- |
| 03/09/2026 | `f0843f0` | Autenticação keyless ADC → IAM `signJwt` → DWD → OAuth e consulta Directory inicial |
| 03/09/2026 | `4d9121f` | Servidor MCP e ferramentas de usuários |
| 07/09/2026 | `aae5f18` | Cache de tokens em memória, serialização e testes MCP de usuários |
| 07/09/2026 | `ee92e06` | Diretrizes de manutenção do Google Workspace Admin MCP |
| 07/09/2026 | `0870c2a` | Listagem de grupos |
| 08/09/2026 | `c9f5fc7` | Listagem de membros de grupos |
| 08/09/2026 | `8ab05e7` | Listagem de unidades organizacionais |
| 10/09/2026 | `6c3cc87` | Listagem de dispositivos móveis |
| 10/09/2026 | `0610ebd` | Listagem de dispositivos ChromeOS |
| 10/09/2026 | `b589a91` | Funções administrativas e atribuições |
| 10/09/2026 | `581b7d9` | Listagem de domínios |
| 10/09/2026 | `c01fd11` | Listagem de aliases de domínio e correções de regressão/serialização |
| 11/09/2026 | `9ce707f` | Implementação local de Buildings: Directory API, serialização, paginação por token e 76/76 testes; após reautenticação manual da ADC pelo usuário, DWD/privilégio delegado confirmados e validação MCP real concluída com 0 Buildings e sem próxima página; checkpoint desta entrega |
| 11/09/2026 | `16565d6` | Resources / Salas: implementação local de `resources.calendars`, serialização limitada, paginação por token, ordenação/filtro e 14ª tool MCP; 100/100 testes locais e validação MCP real da cadeia keyless concluídos com 0 recursos e sem página seguinte; checkpoint registrado nesta entrega |
| 11/09/2026 | checkpoint desta entrega | Features: PLAN, implementação local de `resources.features`, serialização limitada a `feature_name`, paginação por token e 15ª tool MCP; 121/121 testes locais e validação MCP real da cadeia keyless concluídos com 0 Features e sem página seguinte; checkpoint encerra Features e Calendar — recursos corporativos |
| 11/09/2026 | checkpoint pendente | Admin Audit: PLAN, implementação local de `reports.activities.list` com `applicationName=admin`, launcher MCP Python da `.venv`, 16ª tool MCP e 155/155 testes locais; REAL VALIDATION MCP executada uma única vez com sucesso, 1 Activity e próxima página presente; DWD `admin.reports.audit.readonly` e sujeito Superadministrador confirmados manualmente; nenhum conteúdo de auditoria registrado |
| 11/09/2026 | implementação pendente de checkpoint | Login Audit: PLAN e implementação local de `activities.list` com `applicationName=login`, serializer conservador, 17ª tool MCP e **191/191 testes locais aprovados**; REAL VALIDATION e checkpoint Git pendentes; nenhuma chamada Google ou alteração administrativa realizada |
| 11/09/2026 | checkpoint desta entrega | Login Audit: redescoberta pós-restart pelo host, uma única chamada MCP com `max_results=1`, sucesso, 1 Activity e próxima página presente; **191/191 testes locais aprovados** e `git diff --check` aprovado; nenhum conteúdo de Activity, PII, credencial ou token registrado; checkpoint concluído |

## Lições registradas

- O scope ChromeOS não estava autorizado inicialmente; foi incluído antes do
  teste direto e a API retornou HTTP 200 sem dispositivos.
- Para roles, a API retornou 15 funções e 3 atribuições; uma contagem textual
  posterior incorreta não representou falha da integração.
- A primeira redescoberta do catálogo após aliases mostrou um catálogo antigo.
  O encerramento do processo anterior e a reinicialização permitiram ao Codex
  descobrir a ferramenta nova.
- Serializadores auxiliares não devem receber `@mcp.tool()`. A regressão em
  `workspace_users_list` foi corrigida ao restaurar o decorador da ferramenta.
- O checkpoint `c01fd11` também normalizou `test_mcp_protocol.py` para UTF-8
  sem BOM, LF e exatamente uma quebra de linha no EOF.
- Buildings usa `resources.buildings` da Admin SDK Directory API, não a Google
  Calendar API. O scope readonly de recursos de Calendar foi confirmado na DWD
  por um Superadministrador. Depois de o usuário reautenticar manualmente a
  ADC, o processo MCP novo reconheceu a 13ª tool e a única chamada real
  autorizada retornou 0 Buildings, sem próxima página e sem retry.
- Resources / Salas usa a coleção irmã `resources.calendars` e o mesmo scope
  readonly de recursos de Calendar. O módulo encaminha `orderBy` e `query`
  apenas depois de rejeitar valores vazios, preserva o token de página e não
  expõe `kind`, `etags` ou `featureInstances`. Um processo MCP `stdio` novo
  redescobriu a 14ª tool e a única chamada real limitada retornou zero recursos,
  sem página seguinte; nenhum dado administrativo ou material de autenticação
  foi registrado.

- Admin Audit usa a Reports API, não a Directory API: o endpoint fixa
  `applicationName=admin`, enquanto `user_key` filtra o ator e não controla a
  impersonação DWD. A implementação limita páginas a 100 registros, rejeita
  datas não RFC 3339 e omite estruturalmente `sensitiveParameters` e dados
  brutos. A DWD e o privilégio Superadministrador foram confirmados
  manualmente; a única chamada MCP real retornou 1 Activity e próxima página,
  sem registrar conteúdo de auditoria.
- As falhas anteriores ocorreram no ambiente `codexsandboxoffline`: acesso
  bloqueado ao OAuth, `UnsupportedOperation` no `fileno()` de um `stderr` não
  compatível e cache do `uv` sem permissão. O launcher foi remediado para o
  Python da `.venv`; o processo stdio novo inicializou com 16 tools. Nenhuma
  alteração administrativa foi feita.

- Login Audit foi implementado localmente como módulo independente da Reports
  API, com `applicationName=login` fixo, o mesmo scope readonly de auditoria,
  limite MCP de 1–100 por página, paginação explícita sem percurso automático,
  nenhuma nova tentativa e serializer específico com allowlist de valores de
  login. O catálogo passou a 17 tools e a suíte confirmou 191/191 testes
  locais; antes da tentativa 3, REAL VALIDATION e checkpoint Git permaneciam
  pendentes. Nenhum dado real de login, credencial, token, JWT ou alteração
  administrativa foi registrado nessa etapa.
- A linha do histórico operacional foi preservada: tentativa 1 com catálogo
  legado; rediscovery; tentativa 2 em `codexsandboxoffline` com `WinError 10013`;
  diagnóstico de contexto/rede; impossibilidade de restart do host dentro da
  sessão; restart manual do Codex; POST-RESTART CHECK; e tentativa 3 concluída
  pelo MCP do host com uma única chamada bem-sucedida. O resultado foi mantido
  sanitizado, sem Activity, PII ou material de autenticação.

Este histórico resume fatos registrados no Git e no inventário do usuário; não
substitui o `git log`, os testes ou a validação de uma configuração atual do
Google Cloud/Admin Console.
