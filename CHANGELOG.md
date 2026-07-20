# Changelog

All notable changes to AI Novel Workbench are documented here.

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
