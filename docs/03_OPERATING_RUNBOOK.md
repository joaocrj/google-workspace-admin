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
| 403 Directory | privilégio do sujeito delegado, API habilitada e scope da operação |
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
