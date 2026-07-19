# Phase 14 — Release Candidate, First Run, and End-to-End Acceptance

## Version

The release candidate version is:

```text
1.0.0-rc.1
```

`VERSION` is the single source of truth. The backend exposes it through `/api/release/info`; Docker images receive the same value through build arguments and OCI labels; source archives embed it in their release manifest.

## Schema version

Release candidate schema version: **4**.

Migration 4 adds persistent first-run state fields:

- setup payload
- completion timestamp
- last readiness timestamp

Existing databases receive the normal pre-upgrade snapshot and checksum validation before migration 4 is applied.

## Release APIs

- `GET /api/release/info`
- `GET /api/release/readiness`
- `GET /api/setup/state`
- `PUT /api/setup/state`
- `POST /api/setup/complete`
- `POST /api/setup/reset`

Setup completion requires `COMPLETE_SETUP`. When no real model configuration exists, the caller must explicitly acknowledge Stub-only mode.

## First-run wizard

The frontend checks `/api/release/info` when the production shell opens. Incomplete setup opens a lazy-loaded first-run wizard containing:

- semantic version and release channel
- schema current/latest version
- SQLite integrity
- writable data storage
- encrypted credential health
- model configuration status
- independent Worker status
- backup status
- optional administrative token
- explicit Stub-mode acknowledgement

Dismissal is session-only. Successful completion persists in `application_state`.

## Readiness levels

Required checks block setup completion:

- SQLite integrity
- data directory write access
- current, non-drifted migration history
- readable encrypted credentials

Recommended checks produce warnings:

- at least one novel project
- active model configuration and credential
- independent Worker heartbeat
- at least one verified database backup

## Golden path acceptance

The backend acceptance test executes the complete release path on a fresh database:

1. automatically migrate to schema 4
2. create a novel project
3. submit a model through the legacy settings route
4. verify the API key is encrypted and cleared from the ordinary model record
5. run one complete eight-step chapter pipeline
6. verify final chapter, memory, story graph, and rolling plan
7. fork an isolated worldline
8. export an Obsidian Vault and ZIP
9. create a verified SQLite backup
10. pass release readiness
11. complete first-run setup
12. verify plaintext credentials are absent from the SQLite file

## Source artifacts

Build:

```bash
python scripts/build_release.py --output release-dist
```

Verify:

```bash
python scripts/build_release.py --output release-dist --verify
```

Artifacts:

- `ai-novel-workbench-<version>-source.zip`
- `ai-novel-workbench-<version>-manifest.json`
- `SHA256SUMS`
- `release-result.json`

The source archive is deterministic when `SOURCE_DATE_EPOCH` and commit metadata are fixed. CI builds it twice and requires identical SHA-256 digests.

Excluded material includes:

- `.env`
- key files
- SQLite databases
- projects and runtime data
- backups
- dependency directories
- prior release outputs

## Docker release validation

`.github/workflows/release-validation.yml` performs real Docker validation:

1. render `docker compose config`
2. build backend and frontend release images
3. inspect OCI version and revision labels
4. start backend, Worker, and Nginx frontend
5. wait for `/api/release/info`
6. verify schema version 4
7. verify at least one healthy Worker
8. fetch the frontend HTML through Nginx
9. archive Compose state, logs, release info, and runtime health
10. remove containers and the temporary CI data volume

## Controlled publishing

`.github/workflows/release.yml` builds and uploads verified artifacts for manual workflow runs. A GitHub Release is created only when:

- a matching `v<version>` tag is pushed, or
- `publish_release=true` is explicitly approved in a manual workflow dispatch.

No tag or GitHub Release is created merely by merging development pull requests.

## Release candidate limits

- This remains a single-machine SQLite deployment.
- Public TLS and domain routing remain external deployment responsibilities.
- Docker images are validated but not pushed to a public registry without registry authorization.
- `1.0.0-rc.1` is intended for complete acceptance and operational observation before the stable `1.0.0` gate.
