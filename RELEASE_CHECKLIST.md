# Stable Release Checklist

## Source and version

- [ ] `VERSION` is a stable semantic version without prerelease suffix.
- [ ] `CHANGELOG.md` contains the exact version.
- [ ] README, Compose, Dockerfiles, environment examples, tests, and release workflows use the same default version.
- [ ] No unrelated working-tree or generated runtime data is included.

## Dependencies and contracts

- [ ] `backend/requirements.lock` was regenerated on Python 3.12 and has only pinned entries.
- [ ] `frontend/package-lock.json` passes `npm ci` without modification.
- [ ] `docs/openapi.json` matches a freshly generated application contract.
- [ ] `docs/sbom.cdx.json` matches both dependency locks.
- [ ] Python and Node high-severity dependency audits pass.
- [ ] The secret/runtime-data scan reports zero findings.

## Functional acceptance

- [ ] Complete backend suite passes.
- [ ] Complete frontend suite and production build pass.
- [ ] Fresh-process startup reaches the latest schema.
- [ ] Repeated app reloads preserve every explicit API route.
- [ ] Stable golden path completes a chapter, memory, graph, plan, worldline, Obsidian export, backup, and setup.
- [ ] Disaster-recovery drill restores project data and encrypted credentials.

## Deployment acceptance

- [ ] Backend and frontend Docker images build from a clean checkout.
- [ ] OCI labels contain the exact stable version and source commit.
- [ ] Compose config renders successfully.
- [ ] Backend becomes healthy.
- [ ] Nginx frontend responds.
- [ ] Independent Worker reports a healthy heartbeat.
- [ ] Runtime health has no warnings.
- [ ] Backup/restore drill passes with the Worker stopped during restore.

## Release artifacts

- [ ] Source artifacts build twice with identical SHA-256 digests under fixed `SOURCE_DATE_EPOCH`.
- [ ] Embedded and external manifests report the stable version and schema.
- [ ] Archive excludes `.env`, key files, databases, projects, backups, dependency directories, and prior release output.
- [ ] `SHA256SUMS` verifies every distributed file.
- [ ] OpenAPI, SBOM, audit summaries, and preflight report are attached to the release workflow artifact.

## Security and operations

- [ ] Security policy is current.
- [ ] Upgrade and disaster-recovery instructions have been reviewed.
- [ ] A verified off-device database backup exists.
- [ ] The matching master key or secret-manager recovery process is available.
- [ ] Old rotation key material has an explicit retention/deletion decision.
- [ ] Public deployments use TLS, authentication, and a long administrative token.

## Publishing authorization

- [ ] The release commit is known and reviewed.
- [ ] The stable PRs have been merged in dependency order.
- [ ] Explicit authorization to create `v<version>` has been received.
- [ ] Explicit authorization to create the GitHub Release has been received.
- [ ] Registry credentials and explicit authorization exist before publishing images.

The automated release workflows prepare and validate artifacts but do not replace the final publishing authorization checks.
