# Andamento das fases

Última consolidação documental: **11/09/2026**. Esta árvore combina o estado do
código em `master`, os commits e o inventário de validações fornecido pelo
usuário. Atualize-a no mesmo change set de qualquer avanço. Evidência de
produção deve registrar somente status e contagens seguras.

## Convenção de estados e evidências

Os estados formais de entregas são `✅ CONCLUÍDO`, `← EM ANDAMENTO`,
`⬜ PENDENTE` e `⚠️ BLOQUEADO`. Resultados como HTTP 200, contagens, hashes de
commit, VALIDADO, VERIFICADA e ADICIONADO são evidências, não estados
concorrentes; preserve-os como detalhes da entrega.

**Próxima entrega prioritária: Calendar → Features.**

A paginação com `nextPageToken` permanece planejada para a etapa de
**Consolidação da camada Read** e não substitui a próxima entrega prioritária.
Buildings preserva o token por página, sem antecipar essa consolidação global.

```text
FASE 1 — READ / ADMIN INVENTORY
│
├── 1. Directory — identidade e estrutura                 ✅ CONCLUÍDO
│   ├── Users                                              ✅ CONCLUÍDO
│   │   ├── workspace_users_list                           ✅ CONCLUÍDO
│   │   └── workspace_user_get                             ✅ CONCLUÍDO
│   ├── Groups                                             ✅ CONCLUÍDO
│   │   └── workspace_groups_list                          ✅ CONCLUÍDO
│   ├── Group Members                                      ✅ CONCLUÍDO
│   │   └── workspace_group_members_list                   ✅ CONCLUÍDO
│   ├── Organizational Units — Read                        ✅ CONCLUÍDO
│   │   └── workspace_orgunits_list                        ✅ CONCLUÍDO
│   ├── Mobile Devices                                     ✅ CONCLUÍDO
│   │   ├── API Directory e scope readonly                 ✅ CONCLUÍDO
│   │   ├── workspace_mobile_devices_list                  ✅ CONCLUÍDO
│   │   ├── testes unitários/protocolo MCP                 ✅ CONCLUÍDO
│   │   └── revisão + commit                               ✅ CONCLUÍDO — 6c3cc87
│   ├── ChromeOS Devices                                   ✅ CONCLUÍDO
│   │   ├── API Directory                                  ✅ CONCLUÍDO — verificada
│   │   ├── scope chromeos.readonly                        ✅ CONCLUÍDO — adicionado
│   │   ├── teste direto da API                            ✅ CONCLUÍDO — HTTP 200 / 0 dispositivos
│   │   ├── workspace_chromeos_devices_list                ✅ CONCLUÍDO
│   │   ├── testes unitários/protocolo MCP                 ✅ CONCLUÍDO
│   │   ├── execução real MCP/Codex                        ✅ CONCLUÍDO — 0 dispositivos
│   │   └── revisão + commit                               ✅ CONCLUÍDO — 0610ebd
│   ├── Roles & Admins                                     ✅ CONCLUÍDO
│   │   ├── roles.list e roleAssignments.list              ✅ CONCLUÍDO
│   │   ├── scope rolemanagement.readonly                  ✅ CONCLUÍDO — já presente
│   │   ├── teste direto                                   ✅ CONCLUÍDO — 15 roles / 3 assignments
│   │   ├── workspace_roles_list                           ✅ CONCLUÍDO
│   │   ├── workspace_role_assignments_list                ✅ CONCLUÍDO
│   │   ├── execução real MCP/Codex                        ✅ CONCLUÍDO
│   │   └── revisão + commit                               ✅ CONCLUÍDO — b589a91
│   ├── Domains                                            ✅ CONCLUÍDO
│   │   ├── endpoint e scope readonly                      ✅ CONCLUÍDO
│   │   ├── teste direto                                   ✅ CONCLUÍDO — HTTP 200 / 1 domínio
│   │   ├── workspace_domains_list                         ✅ CONCLUÍDO
│   │   ├── testes unitários/protocolo MCP                 ✅ CONCLUÍDO
│   │   └── revisão + commit                               ✅ CONCLUÍDO — 581b7d9
│   └── Domain Aliases                                     ✅ CONCLUÍDO
│       ├── endpoint, scope e filtro parentDomainName      ✅ CONCLUÍDO
│       ├── correção de exposição indevida de serializer   ✅ CONCLUÍDO
│       ├── regressão workspace_users_list corrigida       ✅ CONCLUÍDO
│       ├── execução real MCP/Codex                        ✅ CONCLUÍDO — 1 alias
│       └── revisão + commit                               ✅ CONCLUÍDO — c01fd11
│
├── 2. Calendar — recursos corporativos                   ← EM ANDAMENTO
│   ├── Buildings                                         ✅ CONCLUÍDO
│   │   ├── módulo Directory/resources + tool MCP          ✅ CONCLUÍDO
│   │   ├── paginação por nextPageToken preservada          ✅ CONCLUÍDO — sem percurso automático
│   │   ├── testes unitários/protocolo MCP mockados         ✅ CONCLUÍDO
│   │   ├── descoberta MCP real: 13ª tool                  ✅ CONCLUÍDO — sem serializers expostos
│   │   ├── validação real: DWD + Calendar > View Resources ✅ CONCLUÍDO — 0 Buildings / sem próxima página
│   │   └── revisão + checkpoint                            ✅ CONCLUÍDO — checkpoint desta entrega
│   ├── Resources / Salas                                  ✅ CONCLUÍDO
│   │   ├── módulo Directory/resources + tool MCP          ✅ CONCLUÍDO — sem chamada Google
│   │   ├── paginação por token, ordenação e filtro        ✅ CONCLUÍDO — sem percurso automático
│   │   ├── testes unitários/protocolo MCP mockados        ✅ CONCLUÍDO
│   │   ├── validação real MCP/Codex                       ✅ CONCLUÍDO — 0 Resources / sem próxima página
│   │   └── revisão + checkpoint                           ✅ CONCLUÍDO — checkpoint desta entrega
│   └── Features                                           ⬜ PENDENTE — PRÓXIMA ENTREGA
│
├── 3. Reports / Auditoria                                 ⬜ PENDENTE
│   ├── Admin Audit                                        ⬜ PENDENTE
│   ├── Login Audit                                        ⬜ PENDENTE
│   ├── Drive Audit                                        ⬜ PENDENTE
│   ├── User Usage                                         ⬜ PENDENTE
│   └── Customer Usage                                     ⬜ PENDENTE
│
└── 4. Consolidação da camada Read                         ⬜ PENDENTE
    ├── paginação com nextPageToken                        ⬜ PENDENTE
    ├── tratamento uniforme de erros                       ⬜ PENDENTE
    ├── revisão de scopes mínimos                          ⬜ PENDENTE
    ├── serialização consistente                           ⬜ PENDENTE
    └── inventário/testes finais                           ⬜ PENDENTE

FASE 2 — WRITE / ADMINISTRATION                            ⬜ PENDENTE
│
├── Organizational Units — Write                           ⬜ PENDENTE
│   ├── workspace_orgunit_create                           ⬜ PENDENTE
│   ├── workspace_orgunit_update                           ⬜ PENDENTE
│   ├── workspace_orgunit_move                             ⬜ PENDENTE
│   └── workspace_orgunit_delete                           ⬜ PENDENTE
│
├── Group Management                                       ⬜ PENDENTE
│   ├── criar/atualizar grupos                             ⬜ PENDENTE
│   ├── adicionar/remover membros                          ⬜ PENDENTE
│   └── alterar MEMBER / MANAGER / OWNER                   ⬜ PENDENTE
│
└── User Lifecycle                                         ⬜ PENDENTE
    ├── criar usuário                                      ⬜ PENDENTE
    ├── suspender/reativar                                 ⬜ PENDENTE
    ├── alterar OU                                         ⬜ PENDENTE
    ├── resetar senha                                      ⬜ PENDENTE
    └── administração/delegação                            ⬜ PENDENTE
```

## Evidência de qualidade preservada

- Em 11/09/2026, a implementação local de Buildings confirmou **76/76 testes
  aprovados** em `uv run pytest -v`, incluindo testes unitários, serialização e
  protocolo MCP com mocks. Após reautenticação manual da ADC pelo usuário, a
  suíte foi confirmada novamente com **76/76 testes aprovados** e
  `git diff --check` foi aprovado. Com DWD e privilégio delegado confirmados
  administrativamente, a cadeia keyless ADC → IAM `signJwt` → DWD → OAuth →
  Directory foi validada. Um MCP `stdio` novo descobriu 13 tools e a tool
  Buildings; a única chamada real limitada foi bem-sucedida com zero Buildings
  e sem próxima página. Nenhum nome, endereço, coordenada ou token de
  paginação foi registrado.
- Em 11/09/2026, Resources / Salas recebeu implementação local da coleção
  `resources.calendars`, serialização limitada, paginação por token e testes
  unitários/protocolo MCP com mocks; a suíte completa confirmou **100/100
  testes aprovados**. Um processo MCP `stdio` novo redescobriu 14 tools sem
  helpers/serializers expostos e validou a cadeia keyless com a única chamada
  real limitada a `max_results=1`: zero Resources / Salas e sem próxima página.
  Nenhum dado de recurso, token ou credencial foi registrado. O checkpoint Git
  desta entrega é registrado nesta mudança.
- Na consolidação documental de 10/09/2026, `uv run pytest -v` confirmou
  **56/56 testes aprovados**. `git diff --check` também foi aprovado.
- Em `c01fd11`, o inventário fornecido já registrava **56/56 testes**,
  `git diff --check` e árvore de trabalho limpa.
- A revisão do catálogo concluiu com 12 ferramentas, incluindo aliases e a
  regressão de `workspace_users_list` corrigida.
- A contagem textual de 14 para um retorno de 15 roles foi identificada como
  interpretação do modelo, não erro do MCP.
- Em 11/09/2026, uma reconstrução independente de contexto pelo Codex confirmou
  a coerência da arquitetura keyless, das 12 tools, dos invariantes de
  `server.py`, do checkpoint `c01fd11` e da FASE 1. Essa auditoria não executou
  novamente a suíte; a última evidência executada permanece 56/56 em
  10/09/2026.

Ao executar a suíte novamente, acrescente uma evidência com data e contagem
atuais; não apague o contexto histórico sem uma razão.
