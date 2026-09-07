---
name: google-workspace-admin-maintainer
description: Maintain and extend the Google Workspace Admin MCP using keyless Domain-Wide Delegation, IAM signJwt, ADC, least-privilege scopes, automated tests, and safe administrative tooling.
---

# Google Workspace Admin MCP Maintainer

## Purpose

Maintain, debug, test, document, and extend the `google-workspace-admin` MCP.

The project provides administrative access to Google Workspace APIs through Model Context Protocol (MCP).

Preserve the existing security architecture and avoid changes that weaken the keyless authentication model.

## Project location

Windows project path:

`D:\AI\CODEX\MCP\google-workspace-admin`

Primary package:

`src/google_workspace_admin`

Tests:

`tests`

Python environment and dependency management:

`uv`

## Authentication architecture

The project uses keyless Google Workspace Domain-Wide Delegation.

Authentication flow:

`ADC -> IAM Credentials signJwt -> DWD JWT -> OAuth 2.0 token -> Google Workspace API`

Google Cloud project:

`codex-workspace-admin`

Service Account:

`codex-workspace@codex-workspace-admin.iam.gserviceaccount.com`

The Service Account has Domain-Wide Delegation configured in Google Workspace.

The local Google identity obtains permission to sign JWTs through IAM.

## Security invariants

Never create or require a Service Account JSON private key.

Never store a Service Account private key in the repository.

Never store Google OAuth access tokens or signed JWTs in `.env`, source code, configuration files, logs, tests, or Git.

Never return raw access tokens or signed JWTs through MCP tools.

Do not copy a personal ADC credential file to a VPS or remote server.

Do not replace the keyless DWD architecture with static credentials for convenience.

Treat Domain-Wide Delegation as privileged administrative access.

Use the minimum Google OAuth scopes required by each operation.

Do not allow arbitrary DWD impersonation subjects through an MCP tool.

The default delegated subject must remain controlled by configuration.

If configurable impersonation is introduced later, implement an explicit allowlist.

Prefer read-only administrative tools before write-capable tools.

Write or destructive administrative operations must have explicit validation and appropriate safeguards.

## Authentication implementation

Important modules:

`src/google_workspace_admin/auth/adc.py`

Obtains Application Default Credentials and refreshes them when necessary.

`src/google_workspace_admin/auth/dwd.py`

Builds the DWD JWT payload, calls IAM Credentials `signJwt`, exchanges the signed JWT for a Google Workspace OAuth token, and uses the in-memory token cache.

`src/google_workspace_admin/auth/token_cache.py`

Caches Workspace OAuth access tokens in RAM.

Cache keys must include:

- delegated subject
- normalized scope set

Tokens approaching expiration must not be reused.

The cache must never persist tokens to disk.

## Token behavior

Google Workspace DWD access tokens are short-lived.

The MCP must automatically obtain new tokens when necessary.

Do not require the user to manually authenticate every time a Workspace token expires.

ADC and the generated Workspace access token are different credential layers.

If ADC itself becomes invalid because of Google Cloud authentication or organizational session policy, the user may need to run:

`gcloud auth application-default login`

Do not confuse this with normal Workspace token renewal.

## Directory implementation

Current Directory module:

`src/google_workspace_admin/directory/users.py`

Implemented operations:

- `list_users`
- `get_user`

The user lookup accepts a primary email, alias, or immutable user ID.

Google API responses should not automatically be exposed in full to the model.

Use an explicit serialization boundary in the MCP server.

## MCP server

Server module:

`src/google_workspace_admin/server.py`

Current MCP server name:

`Google Workspace Admin`

Current tools:

- `workspace_status`
- `workspace_users_list`
- `workspace_user_get`

Use `MCPServer` from the installed MCP Python SDK.

Keep the server compatible with stdio transport because the local Codex integration uses stdio.

Do not print arbitrary diagnostic output to stdout while running as an stdio MCP server.

Use stderr or proper logging for diagnostics when needed.

## User serialization

The MCP intentionally exposes selected Directory user fields instead of returning the complete raw Google API object.

Maintain this boundary.

Current user fields include:

- id
- primary_email
- full_name
- given_name
- family_name
- suspended
- archived
- is_admin
- is_delegated_admin
- org_unit_path
- creation_time
- last_login_time

Add new fields only when they are useful for administrative tasks.

Avoid unnecessarily exposing sensitive information.

## Testing strategy

There are three conceptual testing layers.

### Unit tests

Test local behavior without contacting Google.

Examples:

- token cache
- input validation
- serialization
- server functions

### MCP protocol tests

Test MCP registration and calls through an in-memory MCP client.

These tests should not require Google Workspace access when mocks can be used.

### Google integration tests

Test the real chain:

`ADC -> IAM signJwt -> DWD -> Google Workspace API`

Integration tests must be clearly distinguishable from normal unit tests.

Do not make routine test execution unexpectedly perform administrative Google API calls.

## Standard test command

Before committing implementation changes, run:

`uv run pytest -v`

The test suite must pass before creating a checkpoint commit.

Also compile modified Python modules when debugging syntax issues:

`uv run python -m py_compile <path-to-file>`

## Current validated baseline

The project has previously validated:

- ADC authentication
- IAM Credentials `signJwt`
- Domain-Wide Delegation
- OAuth token exchange
- Directory API access
- user listing
- individual user lookup
- in-memory token reuse
- MCP tool registration
- MCP tool execution
- automated unit and MCP protocol tests

Do not remove these capabilities while extending the project.

## Git workflow

Before substantial changes:

1. Run `git status`.
2. Ensure the previous checkpoint is understood.
3. Make focused changes.
4. Run the relevant tests.
5. Run the complete test suite.
6. Review `git diff`.
7. Commit only after tests pass.

Do not automatically discard uncommitted user changes.

Do not rewrite Git history unless explicitly requested.

Prefer focused commits describing the implemented capability.

## Current baseline commits

Important historical checkpoints include:

`f0843f0` — keyless Google Workspace DWD authentication

`4d9121f` — MCP server and Workspace user tools

`aae5f18` — token caching, Workspace user MCP tools, and automated tests

Treat later commits as authoritative if the project evolves.

## Dependency management

Use `uv`.

Add runtime dependencies with:

`uv add <package>`

Add development dependencies with:

`uv add --dev <package>`

Do not manually modify the virtual environment.

Keep `pyproject.toml` and `uv.lock` synchronized.

## Expansion roadmap

Prefer implementing administrative read capabilities before write capabilities.

Suggested order:

1. Users
2. Groups
3. Group members
4. Organizational Units
5. Calendar resources
6. Admin audit activities
7. User usage reports
8. Customer usage reports
9. Drive administrative visibility
10. Gmail administrative capabilities where supported

After the read layer is mature, evaluate controlled write operations such as:

- create user
- update user
- suspend or restore user
- create group
- update group
- add group member
- remove group member
- move user between Organizational Units

Write operations require stronger validation than read operations.

## Scope discipline

Each Google API module should request only the scopes it needs.

Do not automatically request every authorized DWD scope for every token.

A broad set of scopes may be authorized in Google Workspace Admin while individual tools continue using narrower scope sets.

Preserve that separation.

## Error handling

Google HTTP failures should eventually be normalized into useful MCP errors.

Do not expose:

- access tokens
- signed JWTs
- authorization headers
- ADC credential contents

Avoid dumping entire HTTP responses when they may contain authentication details.

Provide enough information to diagnose:

- HTTP status
- API operation
- safe Google error message

## Codex integration

The MCP is intended to be registered as an additional Codex MCP server.

Do not remove, rename, disable, or overwrite existing MCP server configurations when adding this server.

The local MCP should be launched from its own project directory using `uv`.

No Google access token or Service Account private key should be placed in the Codex MCP configuration.

## Remote deployment

The current implementation is local.

If the MCP is later deployed to a VPS or cloud environment, do not copy the user's personal ADC file to that server.

Use an appropriate workload identity mechanism such as:

- attached Google Cloud Service Account
- Workload Identity Federation
- another keyless Google-supported workload identity

Retain the architecture:

`workload identity -> IAM signJwt -> DWD -> Workspace APIs`

Remote deployment should use an appropriate MCP network transport and authentication layer rather than exposing an unauthenticated administrative MCP endpoint.

## Change policy

When modifying this project:

1. Understand the existing implementation before editing.
2. Preserve the keyless security architecture.
3. Make the smallest coherent change.
4. Add or update tests.
5. Validate locally.
6. Validate MCP behavior.
7. Validate Google integration when appropriate.
8. Review security implications.
9. Create a Git checkpoint.

Never trade away the keyless architecture merely to simplify development.