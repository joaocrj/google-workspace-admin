# Contexto obrigatório do projeto

Antes de operar ou alterar este repositório, leia nesta ordem:

1. `docs/00_AGENT_GUIDE.md`
2. `docs/01_GOOGLE_CONFIGURATION.md`
3. `docs/02_MCP_CATALOG.md`
4. `docs/03_OPERATING_RUNBOOK.md`
5. `docs/04_PHASE_STATUS.md`
6. `docs/05_CHANGE_HISTORY.md`

Depois confira `git status --short --branch`, os módulos relevantes, os testes
correspondentes e o histórico Git quando necessário. Preserve alterações do
usuário que não pertencem à tarefa.

Preserve a arquitetura keyless `ADC -> IAM signJwt -> DWD -> OAuth`. Nunca crie
ou registre chaves privadas de Service Account, tokens, JWTs, cabeçalhos de
autorização ou ADC. A camada atual é somente de leitura; mudanças de IAM, DWD,
scopes ou operações administrativas de escrita exigem autorização explícita.

Toda alteração no Google Admin Console ou Google Cloud/Developer — incluindo
DWD, scopes OAuth, IAM, Service Accounts, APIs, consentimento OAuth, funções
ou privilégios administrativos — deve ser previamente solicitada ao usuário e
executada manualmente por ele. O agente/Codex/MCP apenas pesquisa, diagnostica,
explica a mudança necessária e valida posteriormente o resultado.

Preserve também os invariantes estruturais definidos em
`docs/00_AGENT_GUIDE.md`: serializers/helpers não são tools, todas as
`@mcp.tool()` devem ser registradas antes da inicialização e `mcp.run()` deve
permanecer no final absoluto de `server.py`.

O status das fases deve ser atualizado em `docs/04_PHASE_STATUS.md` no formato
de árvore definido no guia sempre que uma entrega avançar, for bloqueada ou for
replanejada. A próxima entrega deve ser obtida desse documento, não inferida
pela ordem de itens pendentes.

Documentação é requisito de conclusão, não uma tarefa posterior. No mesmo
conjunto de mudanças, atualize os documentos afetados: configuração Google e
scopes (`01`), ferramentas e parâmetros (`02`), operação/testes (`03`), árvore
de fases (`04`), marcos/lições (`05`) e o `README` se a navegação ou os comandos
mudaram.
