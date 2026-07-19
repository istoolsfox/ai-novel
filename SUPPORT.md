# Support Policy

## Supported deployment profile

AI Novel Workbench 1.0.0 supports:

- one trusted machine or one trusted server
- Python 3.12
- Node.js 22 for local frontend development
- Docker Compose with the bundled backend, Worker, and Nginx frontend
- Windows PowerShell local launch scripts
- Linux systemd service templates
- SQLite on local persistent storage

The stable release does not claim support for multi-host SQLite, shared network filesystems, Kubernetes, public anonymous access, or horizontally scaled Workers across separate machines.

## Where to ask for help

Use a normal GitHub issue for reproducible bugs, documentation gaps, and feature requests that do not contain secrets or private novel content. Use the private security reporting process in `SECURITY.md` for vulnerabilities.

A useful bug report includes:

- application version from `/api/release/info`
- deployment method
- operating system
- relevant Worker and Web logs
- `/api/runtime/health` output with paths and identifiers redacted when necessary
- migration status from `/api/migrations/status`
- exact reproduction steps using synthetic project text

## Maintenance expectations

Stable 1.0.x maintenance prioritizes:

1. data loss prevention
2. encryption and credential safety
3. migration and restore correctness
4. Worker recovery and task integrity
5. release reproducibility
6. long-form continuity regressions
7. UI defects and usability improvements

## Backward compatibility

- Stable patch releases should preserve database compatibility through checksummed migrations.
- Upgrade rollback restores the selected pre-upgrade snapshot rather than running individual down migrations.
- Model configuration routes retain transparent compatibility with the original settings UI.
- Public API contracts are tracked in `docs/openapi.json`; intentional contract changes must update that snapshot and release notes.

## Unsupported recovery requests

No one can reconstruct an encrypted API key when both the original master key and every verified key backup are lost. Likewise, data removed from all databases and backups cannot be recovered by the application. Maintain separate encrypted, off-device copies of the database backups and master key.
