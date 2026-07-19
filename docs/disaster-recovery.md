# Disaster Recovery Runbook

## Recovery assets

A complete AI Novel recovery requires two independent assets:

1. a verified SQLite backup and its JSON manifest
2. the matching encryption master key, or the external secret-manager recovery process

The database contains encrypted credential ciphertext but not the master key. Restoring only the database can recover projects and chapters while leaving model credentials unreadable when the active key does not match the backup.

## Backup policy

Recommended minimum:

- automatic local backup every 24 hours
- at least 7 scheduled snapshots
- a manual verified backup before upgrades, key rotation, or major story restructuring
- encrypted off-device copies of selected database snapshots
- a separate encrypted copy of the matching `.ai-novel-master.key`
- periodic restore drills using synthetic or copied non-production data

Never place the database backup and unencrypted master key in the same unprotected location.

## Normal database restore

1. Stop the Worker.
2. Confirm no queued, running, or paused generation jobs remain.
3. Confirm no queued or running runtime tasks remain.
4. Verify the selected backup SHA-256 and SQLite integrity.
5. Record the current application version and schema.
6. Use the running Web process, CLI, or operations center to restore.

API confirmation:

```json
{
  "confirmation": "RESTORE"
}
```

The system creates a `pre_restore` safety backup before replacing the active database.

## Matching master-key recovery

After database restore, inspect `/api/security/status`:

- `status=ok` and `unreadable_credentials=0`: the active key matches.
- unreadable credentials: stop Web and Worker, restore the master key that belongs to the database snapshot, then restart Web.

For a file-managed key:

```bash
sudo systemctl stop ai-novel-worker ai-novel-web
cp /secure/off-device/location/.ai-novel-master.key /path/to/data/.ai-novel-master.key
chmod 600 /path/to/data/.ai-novel-master.key
sudo systemctl start ai-novel-web ai-novel-worker
```

For Docker, copy the matching key back into the persistent data volume while all application containers are stopped. For an environment-managed key, restore the matching secret-manager version before restarting containers.

## Docker recovery drill

```bash
# Create and download/record a verified backup through the operations center.
docker compose stop worker

# Perform restore through the UI or API while the Web container remains up.
# When key replacement is required, stop the Web container too:
docker compose stop backend
# restore matching key in the persistent volume or external secret manager
docker compose start backend
# wait for health and migrations
docker compose start worker
```

After restart:

1. `/api/release/info` reports the expected version and schema.
2. `/api/runtime/health` reports no blockers.
3. `/api/security/status` reports zero unreadable credentials.
4. An existing project and finalized chapter open correctly.
5. A credential connection test succeeds.
6. A small generation job completes.
7. A fresh backup is created after recovery.

## Upgrade and key-rotation recovery

- Failed schema migration: automatic snapshot recovery runs before the error is returned.
- Manual upgrade rollback: choose the `pre_upgrade` backup and confirm `ROLLBACK`.
- Failed file-key rotation: the database snapshot and old key are restored automatically.
- Manual key rotation rollback: use the recorded rotation and confirm `RESTORE_KEY` before deleting old-key material.

## Total host loss

On a replacement host:

1. install the same or newer compatible application release
2. initialize an empty data volume
3. stop Web and Worker
4. place the verified SQLite backup at the configured database path
5. place the matching key at the configured key path or restore the secret-manager version
6. start Web with automatic migrations enabled
7. confirm migrations and release readiness
8. start Worker
9. perform the post-recovery validation list above

## Drill evidence

The stable CI suite includes an integrated drill that:

- creates a project, chapter, and encrypted credential
- records database and key recovery material
- rotates the master key and mutates data
- restores the older SQLite snapshot
- restores the matching older master key
- verifies the project, chapter, and credential plaintext through the normal decryption path
- verifies a new post-recovery backup

This automated drill does not replace off-device restore practice on the actual deployment platform.
