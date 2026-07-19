# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 1.0.x | Yes |
| 1.0.0-rc.x | Security fixes only while upgrading to 1.0.x |
| Earlier development branches | No formal support |

## Reporting a vulnerability

Please use GitHub **Security Advisories → Report a vulnerability** for this repository. Do not open a public issue containing API keys, master keys, private project content, database files, exploit details, or recovery material.

Include, when available:

- affected version and deployment method
- operating system and Python/Node versions
- whether Docker, local PowerShell, or systemd is used
- exact endpoint or component
- reproduction steps using synthetic data
- impact and expected behavior
- sanitized logs

Do not attach a real `.env`, `.key`, SQLite database, project directory, or backup archive.

## Security model

AI Novel Workbench is designed for a trusted single-machine or single-host environment.

- Project text and SQLite data are local by default.
- Model API keys are encrypted at rest with Fernet.
- The encryption master key is stored outside SQLite.
- Sensitive mutation endpoints can be protected with `AI_NOVEL_ADMIN_TOKEN`.
- Database migrations create verified pre-upgrade snapshots.
- Master-key rotation verifies every encrypted credential before and after rotation.
- Release archives exclude runtime data, databases, environment files, and key material.

This model does not protect against a fully compromised operating-system account, malicious code running inside the application process, memory scraping while a credential is in use, or an attacker who obtains both the SQLite database and the master key.

## Deployment recommendations

For anything beyond localhost:

1. Set a long random `AI_NOVEL_ADMIN_TOKEN`.
2. Supply `AI_NOVEL_MASTER_KEY` from an external secret manager.
3. Place the bundled service behind TLS and authentication.
4. Restrict access to the persistent data volume and backup directory.
5. Keep the Web and Worker processes on the same trusted host.
6. Run automatic backups and copy verified backups plus the master key to separate encrypted storage.
7. Review `docs/sbom.cdx.json`, dependency audit reports, and the stable release preflight before upgrading.

## Credential handling

- API responses return only masked secret hints.
- Ordinary model configuration records retain only a credential ID.
- Secrets are decrypted in memory immediately before outbound model requests.
- Security events redact nested secret-like fields.
- Generated master-key files use owner-only permissions on POSIX.
- Browser-entered credentials exist in browser memory during submission; avoid untrusted browser extensions.

## Response expectations

A private report should receive acknowledgement after it is reviewed. Remediation priority depends on reproducibility, affected deployment modes, data exposure, and whether a trusted-host assumption has already been violated.
