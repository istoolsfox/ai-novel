# AI Novel Workbench 1.0.0

AI Novel Workbench 1.0.0 is the first stable release of the local-first autonomous long-form fiction system.

## What is included

### Autonomous novel production

A persistent chapter pipeline can create and execute a multi-chapter job through chapter brief, draft, chapter contract, continuity check, automatic repair, recheck, finalization, and memory compilation. Work is stored in SQLite and executed by an independent Worker with heartbeats, leases, retries, pause/resume/stop controls, and stale-work recovery.

### Long-form memory and planning

The system maintains hard facts, character states, knowledge boundaries, relationships, item ownership, narrative debts, foreshadowing, multi-thread story graphs, story nodes and edges, impact propagation, stalled-thread detection, and rolling future chapter plans.

### Worldlines and knowledge export

Writers can fork isolated worldlines from an existing chapter, activate or promote a branch, archive alternatives, and compare chapter, memory, graph, and plan differences. Every worldline can export its own incremental Obsidian Vault, Canvas files, manifest, and ZIP archive.

### Unified control experience

The React interface includes the original writing workbench plus lazy-loaded centers for autonomous generation, operations, encrypted credentials, database upgrades, and first-run readiness. The story graph supports draggable nodes, and worldline comparisons are available without changing stored content.

### Reliability and recovery

The stable release includes runtime health diagnostics, asynchronous exports, verified SQLite backups, scheduled backup retention, guarded restore, checksummed migrations, pre-upgrade snapshots, failed-migration automatic recovery, explicit rollback, file-managed master-key rotation, and matching-key restoration.

### Security and supply chain

Model API keys are encrypted at rest and removed from ordinary model configuration records. The stable gate pins Python dependencies, verifies the Node lockfile, commits an OpenAPI contract, generates a CycloneDX SBOM, scans source for credentials and runtime data, and runs Python and Node vulnerability audits.

### Deployment and release engineering

Supported single-machine deployment paths include Docker Compose, Windows PowerShell, and Linux systemd templates. Release artifacts are deterministic under a fixed source timestamp, include SHA-256 manifests, and exclude environment files, databases, keys, projects, backups, and dependency directories.

## Upgrade from 1.0.0-rc.1

1. Stop the independent Worker.
2. Create and verify a database backup.
3. Copy the matching master key to separate encrypted storage.
4. Update the source or images.
5. Start the Web service and allow known migrations to complete.
6. Start the Worker only after Web health is green.
7. Verify `/api/release/info`, `/api/runtime/health`, and `/api/security/status`.

The schema remains version 4. The stable release adds release gates, locked dependencies, contracts, recovery drills, and documentation rather than a new application schema migration.

## Known boundaries

- SQLite and the lease queue target one trusted host.
- Public TLS, identity, and domain routing are external responsibilities.
- A fully compromised operating-system account is outside the encryption threat model.
- Public image registry publication is not automatic.
- Git tags and GitHub Releases require explicit operator authorization.

## Verification

Before publishing, follow `RELEASE_CHECKLIST.md` and retain the stable gate reports, source archive checksums, SBOM, OpenAPI snapshot, dependency audits, Docker smoke logs, and disaster-recovery drill result.
