# Upgrading AI Novel Workbench

## Before every upgrade

1. Read `CHANGELOG.md` and the release notes for the target version.
2. Confirm `/api/runtime/health` has no stale leases or failed storage checks.
3. Stop the independent Worker.
4. Finish or cancel queued, running, and paused generation jobs.
5. Finish queued and running runtime tasks.
6. Create and verify a manual database backup.
7. Copy the database backup and the active master key to separate encrypted storage.
8. Run the release preflight for the new source tree.

## Docker Compose upgrade

```bash
docker compose stop worker
docker compose exec backend python -m backend.app.migration_cli status
docker compose exec backend python -m backend.app.migration_cli plan
docker compose exec backend python -m backend.app.migration_cli apply
docker compose up -d --build
```

The Web container defaults to `AI_NOVEL_AUTO_MIGRATE=1` and applies known migrations before becoming healthy. The Worker container uses `AI_NOVEL_AUTO_MIGRATE=0` and starts after the Web health check. Manual planning is still recommended before a stable upgrade.

## Local or systemd upgrade

Stop the Worker first:

```bash
sudo systemctl stop ai-novel-worker
python -m backend.app.migration_cli status
python -m backend.app.migration_cli plan
python -m backend.app.migration_cli apply
sudo systemctl restart ai-novel-web
sudo systemctl start ai-novel-worker
```

For Windows local mode, use `scripts/windows/stop-local.ps1`, update dependencies from `backend/requirements.lock` and `frontend/package-lock.json`, then restart with `start-local.ps1`.

## Migration safety

- Applied migrations have fixed versions and SHA-256 checksums.
- Checksum drift or unknown versions block automatic migration.
- A verified `pre_upgrade` SQLite snapshot is created before pending migrations.
- A failing migration automatically restores the snapshot.
- Migration runs record the planned versions, applied versions, backup ID, duration, and error.

## Rolling back an upgrade

Rollback restores all application data to the selected snapshot point.

```bash
python -m backend.app.migration_cli runs
python -m backend.app.migration_cli rollback <pre-upgrade-backup-id>
```

The API and upgrade center require the explicit confirmation `ROLLBACK`. A `pre_restore` safety backup is created before the selected snapshot replaces the active database.

## Master-key changes

File-managed master keys can be rotated through the upgrade center or CLI:

```bash
python -m backend.app.migration_cli rotate-key
```

The operation decrypts every credential, creates a database snapshot and old-key backup, re-encrypts all credentials, atomically replaces the key, and verifies every new ciphertext.

When `AI_NOVEL_MASTER_KEY` comes from an external secret manager, in-application rotation is blocked. Coordinate external key replacement and database re-encryption during a maintenance window.

## After upgrading

1. Verify `/api/release/info` reports the expected semantic version and current schema.
2. Verify `/api/runtime/health` reports a healthy Worker.
3. Open an existing project and read a finalized chapter.
4. Run a small Stub-mode or test-model generation job.
5. Verify an encrypted credential can complete a connection test.
6. Create and download a fresh database backup.
7. Export one Obsidian Vault and confirm the ZIP opens.
8. Keep the pre-upgrade snapshot and key rollback material until the observation period is complete.
