# Changelog

All notable changes to AI Novel Workbench are documented here.

## 1.0.0 — 2026-07-20

### Stable release

- promoted the fully validated release candidate to the first stable release
- added pinned Python dependency locking and frontend lockfile verification
- added CycloneDX software bill of materials generation
- added committed OpenAPI contract generation and drift detection
- added source secret scanning and high-severity dependency vulnerability gates
- added an integrated disaster-recovery drill covering database and encrypted credential recovery
- added a stable release preflight report, maintenance documentation, support policy, security policy, and release checklist
- retained controlled publishing: no GitHub tag, Release, or public image push occurs without explicit authorization

### Validation inherited from the release candidate

- persistent autonomous chapter pipeline and independent Worker execution
- layered memory, continuity enforcement, story graph, impact propagation, rolling plans, and isolated worldlines
- Obsidian Vault/Canvas export, unified control centers, draggable graph, and worldline comparison
- runtime health, lease recovery, verified backups, guarded restore, scheduled backups, and deployment tooling
- encrypted local model credentials, checksummed migrations, snapshot rollback, and master-key rotation
- deterministic source archives, OCI-labelled Docker images, Compose smoke validation, and golden-path acceptance

## 1.0.0-rc.1 — 2026-07-20

### Autonomous writing runtime

- persistent multi-chapter generation jobs with pause, resume, stop, retry, progress events, and independent Worker execution
- chapter briefs, drafts, contracts, continuity checking, repair, recheck, finalization, and memory compilation
- stale lease recovery and Worker heartbeat diagnostics

### Long-form consistency

- layered hard facts, character state, knowledge boundaries, relationships, items, narrative debts, and foreshadowing
- multi-thread story graph with nodes, edges, focus recommendations, and stalled-thread detection
- impact propagation and rolling chapter planning with lockable plans
- isolated worldline forks, activation, promotion, archival, and difference comparison

### Authoring and visualization

- unified autonomous control center
- draggable story graph canvas
- worldline comparison panel
- Obsidian Vault, Canvas, manifest, incremental export, and ZIP download

### Reliability and operations

- independent SQLite lease Worker and asynchronous exports
- runtime health, diagnostics, event logs, database backups, guarded restore, and automatic scheduled backups
- Docker Compose, Windows PowerShell launchers, and systemd templates
- operations center for Workers, tasks, logs, backups, restore, and deployment commands

### Security and upgrades

- encrypted local model credentials with masked APIs and transparent legacy settings migration
- optional administrative token for sensitive mutation endpoints
- checksummed schema migrations, upgrade snapshots, drift detection, automatic failed-migration restore, and explicit rollback
- verified master-key rotation and previous-key recovery

### Release candidate

- semantic version endpoint and release metadata
- first-run readiness and setup workflow
- source release archives with SHA-256 manifests
- Docker image build validation and full golden-path end-to-end acceptance tests

## Pre-1.0 development

The functionality above was developed in sequential phases and remains available in the stacked development pull requests preceding this release candidate.
