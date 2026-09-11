---
name: google-workspace-admin-maintainer
description: Maintain and extend the Google Workspace Admin MCP using keyless DWD, least-privilege scopes, safe MCP registration, automated tests, and the repository documentation as the current project context.
---

# Google Workspace Admin MCP Maintainer

## Purpose

Maintain, debug, test, document, and extend the `google-workspace-admin` MCP
without weakening its keyless authentication architecture or bypassing the
project's documented development process.

Project path:

`D:\AI\CODEX\MCP\google-workspace-admin`

Use `uv` for Python environment and dependency management.

## Mandatory context loading

Before planning or editing, read the repository's maintained context in this
order:

1. `docs/00_AGENT_GUIDE.md`
2. `docs/01_GOOGLE_CONFIGURATION.md`
3. `docs/02_MCP_CATALOG.md`
4. `docs/03_OPERATING_RUNBOOK.md`
5. `docs/04_PHASE_STATUS.md`
6. `docs/05_CHANGE_HISTORY.md`

Then inspect `git status --short --branch`, the relevant source modules and
tests, and Git history when historical context is necessary.

Do not maintain a second copy of the current tool catalog, roadmap, or commit
history in this Skill. Read `02_MCP_CATALOG.md`, `04_PHASE_STATUS.md`, and
`05_CHANGE_HISTORY.md` for those dynamic facts.

If code, tests, Git, and documentation disagree, investigate using the
source-of-truth order defined in `00_AGENT_GUIDE.md`.

## Authentication architecture

Preserve:

`ADC -> IAM Credentials signJwt -> DWD JWT -> OAuth 2.0 token -> Google Workspace API`

Never create or require a Service Account JSON private key. Never store or
expose OAuth access tokens, signed JWTs, authorization headers, ADC contents,
cookies, or secrets in source, `.env`, tests, docs, logs, MCP responses, or
Git. Never copy personal ADC credentials to a VPS or another device.

Keep the delegated subject controlled by configuration. Do not make arbitrary
DWD impersonation an MCP parameter. Each API operation must request only the
scopes it needs. Do not broaden DWD or change IAM/Google Admin configuration
merely for convenience.

The current Google configuration and scope state belong in
`docs/01_GOOGLE_CONFIGURATION.md`.

## Project safety invariants

- Preserve unrelated user changes.
- Do not remove, rename, disable, overwrite, or reconfigure other Codex MCP
  servers while working on this project.
- The local MCP uses `stdio`; never write arbitrary diagnostics to `stdout`.
  Use `stderr` or proper logging.
- Do not expose raw Google API objects when an explicit serializer can limit the
  response to useful administrative fields.
- Write, delete, IAM, DWD, scope, or destructive administrative operations
  require explicit user authorization and the safeguards defined for the
  write-capable phase.

## Critical `server.py` invariants

In `src/google_workspace_admin/server.py`:

1. `@mcp.tool()` is only for functions intentionally exposed as MCP tools.
2. Serializers and helper functions must never receive `@mcp.tool()`.
3. Every MCP tool must be defined and registered before server startup.
4. `if __name__ == "__main__":` and `mcp.run()` must remain at the absolute end
   of the file.
5. Nothing that must register with the MCP may be placed after `mcp.run()`.

This is functional, not stylistic. Running
`python -m google_workspace_admin.server` blocks at `mcp.run()`. Code below it
may behave differently in import-based tests from the real Codex server
process.

After changing tool registration, validate protocol tests and the actual MCP
catalog when appropriate. If the implementation and direct catalog are correct
but Codex shows an old catalog, treat stale Codex/MCP processes as a likely
cause and perform controlled restart/rediscoberta before changing working code.

## Mandatory workflow

### 1. READ

Read all mandatory project documents, check `git status --short --branch`,
inspect the relevant implementation and tests, identify the current phase and
next pending delivery from `docs/04_PHASE_STATUS.md`, and preserve unrelated
user changes.

### 2. PLAN

Before coding, verify current official Google documentation and confirm the
API/service, endpoint, parameters, limits, pagination behavior, delegated
privileges, and minimum OAuth scope. Determine whether the API/scope is already
configured and whether real integration validation is necessary and
authorized.

Do not change Google Cloud, IAM, DWD, Admin Console, or scopes preemptively.

### 3. IMPLEMENT

Put API access in the appropriate package such as `directory/`, `reports/`, or
another coherent layer. Request only the scope required by that module. Use
bounded HTTP timeouts, validate parameters and documented limits, use an
explicit serializer, expose only fields required for the task, preserve all
`server.py` structural invariants, and make the smallest coherent change.

### 4. TEST

Use focused tests while developing. Compile modified Python modules when
appropriate. Before completion, run the routine suite and checks defined in
`docs/03_OPERATING_RUNBOOK.md`.

MCP protocol tests must validate intended registration and invocation without
requiring real Google access when mocks are sufficient. Routine tests must not
unexpectedly perform privileged Google API calls.

### 5. REAL VALIDATION

Perform real Google integration only when necessary and authorized. Make the
smallest useful read request, record only safe operation/status/count evidence,
never persist credentials or unnecessary personal data, and confirm the
response passes through the intended MCP serializer.

When a new tool is introduced, real Codex discovery/execution may be part of
the delivery evidence.

### 6. DOCUMENT

Documentation is part of the definition of done. Update every affected
document in the same change set:

- `01_GOOGLE_CONFIGURATION.md` for Google configuration, scopes, APIs, IAM/DWD,
  or authentication behavior;
- `02_MCP_CATALOG.md` for tools, modules, parameters, endpoints, limits, or
  catalog behavior;
- `03_OPERATING_RUNBOOK.md` for commands, validation, troubleshooting, or
  operational procedures;
- `04_PHASE_STATUS.md` whenever a delivery starts, completes, blocks, or is
  replanned;
- `05_CHANGE_HISTORY.md` for meaningful checkpoints and lessons;
- `README.md` when navigation or user-facing setup/commands change;
- `00_AGENT_GUIDE.md` when project-wide agent rules or invariants change.

Do not copy dynamic catalog, roadmap, or history back into this Skill.

### 7. COMMIT

Before a checkpoint, run the complete applicable test suite, run
`git diff --check`, review the diff/status, stage only intended files, run
`git diff --cached --check`, review the staged diff/stat, and create a focused
commit only after validation passes.

Do not rewrite Git history unless explicitly requested.

## Testing model

Maintain three distinct layers:

- **Unit tests:** local validation, serializers, cache, API modules, server
  functions.
- **MCP protocol tests:** tool registration, invocation, validation, and
  serialization without real Google access when mocks suffice.
- **Google integration tests:** the real
  `ADC -> IAM signJwt -> DWD -> Google Workspace API` chain when appropriate.

Keep integration diagnostics separate from routine tests unless the project
explicitly changes that policy.

## Token and ADC behavior

Workspace DWD access tokens are short-lived and should be renewed automatically
by the MCP. Do not require manual login merely because a Workspace token
expires.

If the underlying ADC becomes invalid because of Google Cloud authentication
or organizational session policy, the user may need:

`gcloud auth application-default login`

That is ADC reauthentication, not normal Workspace token renewal.

## Dependency management

Use `uv add <package>` or `uv add --dev <package>`. Do not manually modify the
virtual environment. Keep `pyproject.toml` and `uv.lock` synchronized.

## Remote deployment

Never copy personal ADC credentials to a remote server. A future remote
deployment must preserve a keyless workload identity pattern, for example:

`workload identity -> IAM signJwt -> DWD -> Workspace APIs`

It must also use an authenticated MCP network transport rather than exposing an
unauthenticated administrative endpoint.

## Progress reporting

Use the exact status-tree conventions from `docs/00_AGENT_GUIDE.md`. Do not
infer the next implementation from this Skill; read `docs/04_PHASE_STATUS.md`.

## Completion rule

A capability is complete only when the applicable implementation, automated
tests, MCP behavior, authorized real validation, documentation, diff checks,
and Git checkpoint requirements have been satisfied.
