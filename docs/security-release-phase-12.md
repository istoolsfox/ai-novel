# Phase 12 — Security and Release Foundation

## Scope

This phase removes model API secrets from ordinary project records and introduces a local encrypted credential store. It also adds a lazy frontend security center, optional administrative mutation token, automatic migration of legacy plaintext model configuration keys, and regression tests that assert plaintext is absent from SQLite and API responses.

## Master key

The credential store uses Fernet authenticated encryption from `cryptography`.

Resolution order:

1. `AI_NOVEL_MASTER_KEY`, suitable for Docker secrets or a host secret manager.
2. `AI_NOVEL_MASTER_KEY_FILE` when an explicit key file location is required.
3. A generated `.ai-novel-master.key` beside the SQLite database.

On POSIX systems a generated key file is created with owner-only `0600` permissions. The file and generic `*.key` patterns are ignored by Git.

The master key is not stored in SQLite. Losing the master key makes existing encrypted credentials unrecoverable. Back up the key separately from database snapshots.

## Credential lifecycle

Security APIs:

- `GET /api/security/status`
- `GET /api/security/events`
- `GET /api/security/projects/{project_id}/credentials`
- `POST /api/security/projects/{project_id}/credentials`
- `PATCH /api/security/projects/{project_id}/credentials/{credential_id}`
- `DELETE /api/security/projects/{project_id}/credentials/{credential_id}`
- `POST /api/security/projects/{project_id}/credentials/{credential_id}/test`
- `POST /api/security/migrate-plaintext-model-configs`

Responses contain a short hint such as `sk-••••xyz`, never the secret. Decryption is limited to an in-memory model request or explicit connection test.

## Legacy model settings

The existing model settings page continues to submit its familiar payload. The backend transparently intercepts `model-configs` create and update operations:

1. Extract `payload.api_key`.
2. Create or rotate an encrypted credential.
3. Replace the ordinary field with an empty string.
4. Store only `credential_id` and `credential_hint` in the model configuration.

Existing SQLite rows containing plaintext `payload.api_key` are migrated during application initialization. Model execution resolves `credential_id`, decrypts in memory, and passes the secret directly to the outbound request headers.

## Administrative token

When `AI_NOVEL_ADMIN_TOKEN` is empty, local credential operations remain available without authentication, matching the local-first desktop workflow.

When configured, credential create/update/delete/test and plaintext migration require either:

- `X-AI-Novel-Admin-Token: <token>`
- `Authorization: Bearer <token>`

The frontend security center keeps this token only in browser `sessionStorage`.

## Frontend

The new **安全中心** is a separately lazy-loaded chunk. It supports:

- security and key fingerprint status
- project credential listing
- masked secret hints
- credential creation
- secret rotation
- enable/disable
- connection testing
- deletion
- security event history
- optional administrative token

## Security properties

- authenticated encryption at rest
- no plaintext secret in credential API responses
- no plaintext secret in security events
- ordinary model configuration rows store only credential references
- nested secret-like fields are redacted before event persistence
- generated master key files are owner-only on POSIX
- optional administrative token for mutation endpoints

## Limits

- This protects secrets at rest, not a fully compromised host process.
- Browser requests can still contain a newly entered secret before it reaches the local backend.
- A master key rotation utility is intentionally deferred to the migration phase so rotation can create a verified rollback snapshot.
- Public multi-user authentication is not included; the target remains a trusted single-machine deployment.
