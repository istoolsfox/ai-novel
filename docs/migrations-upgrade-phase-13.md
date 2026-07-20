# Phase 13 — Versioned Migrations, Upgrade Rollback, and Master-Key Rotation

## Goals

Phase 13 replaces ad-hoc schema evolution with a checksummed migration registry and makes every destructive maintenance operation recoverable.

The upgrade contract is:

1. inspect migration history and checksums
2. block when Workers or active tasks exist
3. create and verify a `pre_upgrade` SQLite snapshot
4. apply migrations in version order
5. record duration, checksum, snapshot, and applied versions
6. restore the snapshot automatically if any migration fails
7. expose an explicit rollback path for operators

## Schema tables

- `schema_migrations`: one immutable row per applied migration
- `migration_runs`: each apply attempt, including rolled-back attempts
- `application_metadata`: durable schema feature markers
- `application_state`: release channel, installed version, and first-run progress
- `master_key_rotations`: rotation fingerprints, backup material, status, and errors

Current schema version: **3**.

## Migration API

- `GET /api/migrations/status`
- `GET /api/migrations/plan`
- `GET /api/migrations/runs`
- `POST /api/migrations/apply` with `{ "confirmation": "APPLY" }`
- `POST /api/migrations/rollback/{backup_id}` with `{ "confirmation": "ROLLBACK" }`

Checksum drift or unknown applied versions set migration status to `drift` and block automatic application.

## Automatic startup migration

Production startup defaults to:

```env
AI_NOVEL_AUTO_MIGRATE=1
```

The Web process applies migrations before it becomes healthy. The Docker Worker sets `AI_NOVEL_AUTO_MIGRATE=0` and starts only after the Web health check succeeds, preventing concurrent schema changes.

Set `AI_NOVEL_AUTO_MIGRATE=0` to require manual application through the CLI or upgrade center.

## CLI

```bash
python -m backend.app.migration_cli status
python -m backend.app.migration_cli plan
python -m backend.app.migration_cli apply
python -m backend.app.migration_cli runs
python -m backend.app.migration_cli rollback <backup-id>
python -m backend.app.migration_cli rotate-key
python -m backend.app.migration_cli key-history
python -m backend.app.migration_cli restore-key <rotation-id>
```

Web, Worker, and queued work must be stopped before apply, rollback, key rotation, or key restoration.

## Master-key rotation

File-managed master keys support verified rotation:

1. ensure no active Workers or work
2. decrypt every credential with the current key before changing anything
3. create a verified `pre_key_rotation` database snapshot
4. create an owner-only copy of the current key
5. re-encrypt every credential in one database transaction
6. atomically replace the key file
7. decrypt every new ciphertext and verify the new fingerprint
8. record the completed rotation

Any error restores both the database snapshot and previous key.

When `AI_NOVEL_MASTER_KEY` is supplied by the environment, in-app key rotation is blocked. Rotate the external secret through the deployment secret manager and coordinate the database re-encryption during maintenance.

## Key rotation API

- `GET /api/security/master-key/rotations`
- `POST /api/security/master-key/rotate` with confirmation `ROTATE`
- `POST /api/security/master-key/rotations/{rotation_id}/restore` with confirmation `RESTORE_KEY`

## Frontend upgrade center

The lazy-loaded **升级中心** displays:

- current/latest schema versions
- pending migration descriptions and checksums
- drift and unknown versions
- active Worker/task blockers
- migration run history
- upgrade snapshot IDs
- explicit apply and rollback confirmations
- master-key fingerprints and rotation history
- key rotation and key restore confirmations

## Safety boundaries

- Snapshot rollback is the supported migration rollback mechanism; individual down migrations are intentionally avoided.
- Rollback can restore application data to the selected snapshot point.
- Key backup files are sensitive and use owner-only permissions on POSIX.
- Old key backup material should be removed only after the release has been observed and validated.
- Schema migration does not replace full off-device backups.
