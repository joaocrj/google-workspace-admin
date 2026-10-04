# Guia de contexto para Codex e outros agentes

## Missão e limites

Este repositório implementa o **Google Workspace Admin MCP**, um servidor MCP
local, somente de leitura, para um operador técnico ou administrador de TI. O
MVP configura uma organização Google Workspace por runtime e usa um host MCP
conversacional externo via `stdio`. O catálogo público tem 24 ferramentas e
zero ferramentas de escrita.

O MVP inclui leitura administrativa selecionada, Reports, descoberta/inventário
de Shared Drives, Google Docs Content e Google Sheets Content após validação
final. UI gráfica própria, multi-tenant, serviço remoto, self-service de
funcionários e operações públicas de escrita são fases futuras, não requisitos
do MVP. Consulte `docs/04_PHASE_STATUS.md` para o roadmap canônico A–F.

O perfil regional padrão brasileiro da fixture é `pt_BR` e
`America/Sao_Paulo`; o idioma humano principal é português do Brasil. O reader
de produção permanece locale-agnostic e timezone-agnostic. A implementação
Google Sheets 1.5.5 está completa; o contrato regional, o reparo canônico da
fixture e a validação real final foram concluídos. A evidência confirmou
`locale=pt_BR`, `timeZone=America/Sao_Paulo`, K1/L1 canônicos, fórmula O1 e
omissão trailing válida em P1; `PRODUCT DEFECT = NO` e
`PRODUCTION_READER_DEFECT = NO`. Nenhum gate Sheets de implementação ou validação real está pendente.
LOCAL GIT CHECKPOINT = COMPLETE; POST-CHECKPOINT VERIFICATION = COMPLETE.

A implementação técnica e a validação real do Workspace Content Google Sheets
1.5.5 estão concluídas. LOCAL GIT CHECKPOINT = COMPLETE — HEAD db817b6d38d67b39287f91686c995f6eb318565f;
parent a88110730db23ccd43e8c4ac030e113945f20114; exatamente 49 caminhos aprovados commitados.
A correção histórica do allow-list confirmou src/google_workspace_admin/server.py como canônico;
src/google_workspace_admin/content/server.py não existe no repositório. POST-CHECKPOINT VERIFICATION = COMPLETE;
immediately after commit, worktree = CLEAN and staging = EMPTY.
REMOTE SYNCHRONIZATION = NOT PERFORMED; no push/rebase/merge occurred. Repository documentation
registra estado e histórico, mas não é autorização para futuras operações Git, Google, runner
ou operação administrativa. Gates anteriores são históricos, não ponteiros ativos.

Antes de atuar, leia:

1. este arquivo;
2. `docs/01_GOOGLE_CONFIGURATION.md`;
3. `docs/02_MCP_CATALOG.md`;
4. `docs/03_OPERATING_RUNBOOK.md`;
5. `docs/04_PHASE_STATUS.md`;
6. `docs/05_CHANGE_HISTORY.md`.

Se estiver atuando por uma Skill, ela deve orquestrar esse contexto, não
substituí-lo.

Depois confira `git status --short --branch`, o módulo que será alterado e os
testes correspondentes. Preserve alterações do usuário que não pertencem à
tarefa.

## Fonte de verdade e evidência

Use esta ordem de confiança:

1. código em `src/google_workspace_admin/` e testes em `tests/`;
2. configuração rastreada, `pyproject.toml` e histórico Git;
3. documentação em `docs/`;
4. resultados novos, reproduzíveis e seguros de testes;
5. anotações históricas fornecidas pelo usuário.

O inventário recebido em 10/09/2026 foi incorporado ao status de fases. Não
deduza de um marcador histórico que uma concessão ainda existe: valide antes de
alterar Google Cloud ou Admin Console.

## Invariantes de segurança

- Não criar, baixar, versionar ou pedir chave privada JSON de Service Account.
- Não registrar tokens OAuth, JWTs assinados, cabeçalhos `Authorization`, ADC,
  cookies ou conteúdo de `.env`.
- Não copiar a ADC pessoal para VPS, repositórios ou outros dispositivos.
- Manter o sujeito delegado controlado pela configuração; uma ferramenta MCP
  não pode aceitar arbitrariamente um e-mail para impersonação.
- Solicitar autorização explícita antes de qualquer operação administrativa de
  escrita, exclusão, mudança de escopo ou alteração em IAM/DWD.
- Toda alteração no Google Admin Console ou Google Cloud/Developer, incluindo
  DWD, scopes OAuth, IAM, Service Accounts, APIs, consentimento OAuth, funções
  e privilégios administrativos, deve ser solicitada previamente ao usuário e
  executada manualmente por ele. O agente/Codex/MCP limita-se a pesquisar,
  diagnosticar, especificar a configuração necessária e validar o resultado.
- Usar o menor conjunto de scopes por chamada e não expor respostas brutas da
  API ao modelo quando um serializador já seleciona os campos necessários.
- O servidor MCP é `stdio`: diagnósticos vão para `stderr`/logging, nunca para
  `stdout` arbitrário.

## Invariantes estruturais do servidor MCP

Em `src/google_workspace_admin/server.py`:

- `@mcp.tool()` deve decorar somente funções intencionalmente expostas como
  ferramentas MCP.
- Serializadores e funções auxiliares nunca devem receber `@mcp.tool()`.
- Todas as definições de ferramentas MCP devem ser executadas antes de iniciar
  o servidor.
- O bloco `if __name__ == "__main__":` com `mcp.run()` deve permanecer no
  **final absoluto** de `server.py`.
- Não coloque ferramentas, serializadores, helpers ou lógica de registro depois
  de `mcp.run()`.

Esse posicionamento é funcional. Quando o servidor é iniciado com
`python -m google_workspace_admin.server`, a execução bloqueia em `mcp.run()`.
Uma ferramenta definida abaixo dele pode aparecer em testes que apenas importam
o módulo, mas não ser registrada no processo real iniciado pelo Codex.

Depois de alterar registros de ferramentas, valide os testes de protocolo e o
catálogo MCP. Se código e testes estiverem corretos, mas o Codex continuar
mostrando um catálogo antigo, considere processo MCP/Codex obsoleto e faça uma
reinicialização/redescoberta controlada antes de modificar código funcional.

## Fluxo obrigatório para uma capacidade nova

1. Confirmar a necessidade, API, endpoint, permissões do usuário delegado e
   menor scope OAuth viável na documentação oficial do Google.
2. Verificar se o serviço/API e o scope já existem. Não ampliar DWD por
   conveniência.
3. Criar um módulo de API em `directory/`, `reports/` ou outra camada adequada;
   cada chamada deve pedir apenas o scope dela.
4. Criar um serializador explícito e uma ferramenta MCP validando parâmetros e
   limites de paginação.
5. Adicionar testes unitários e de protocolo MCP sem acesso real ao Google.
6. Executar `uv run pytest -v`, revisar `git diff --check` e testar a
   integração real somente quando ela for necessária e autorizada.
7. Atualizar, no mesmo change set, toda a documentação afetada: configuração
   Google/scopes (`01`), catálogo MCP (`02`), runbook (`03`), árvore de fases
   (`04`), marcos e lições (`05`) e `README` quando a navegação ou comandos
   mudarem. Só então criar o checkpoint Git solicitado pelo usuário.

Documentação é parte da definição de pronto. Não adie sua atualização para uma
tarefa futura nem marque a entrega como concluída se o comportamento, a
segurança, os testes ou o andamento deixaram de corresponder aos documentos.

## Formato obrigatório de andamento

Sempre que uma fase for reportada ou atualizada, use uma árvore monoespaçada,
com uma legenda inequívoca:

```text
FASE N — NOME
│
├── Entrega A                                      ✅ CONCLUÍDO
│   ├── validação                                   ✅
│   └── próximo passo                               ← EM ANDAMENTO
└── Entrega B                                      ⬜ PENDENTE
```

Marcadores permitidos: `✅ CONCLUÍDO`, `← EM ANDAMENTO`, `⬜ PENDENTE` e
`⚠️ BLOQUEADO`. Atualize `docs/04_PHASE_STATUS.md` no mesmo conjunto de
mudanças que concluir, iniciar, bloquear ou replanejar uma entrega. Não declare
uma integração Google concluída sem registrar o resultado seguro (por exemplo,
HTTP 200 e contagem, nunca credenciais ou dados pessoais desnecessários).
