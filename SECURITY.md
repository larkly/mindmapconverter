# Security Policy

This document describes how to report security vulnerabilities for this repository.

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Instead, use GitHub's **Private Vulnerability Reporting**:

1. Navigate to the **Security** tab of this repository on GitHub.
2. Click **Report a vulnerability**.
3. Fill in the form with details: affected component, version, reproduction steps, and impact.

You will receive an acknowledgement within **5 business days**. If the report is accepted, you will be kept informed of remediation progress and notified when a fix is released.

## Scope

This policy covers security vulnerabilities in:

- Source code in this repository
- Published release artifacts produced by this repository's CI (binaries, container images, packages)
- CI/CD workflows when they affect release integrity

Out of scope:

- Vulnerabilities in third-party dependencies that have not been patched upstream (report to the upstream maintainer; consider opening a Dependabot advisory if you are a maintainer)
- Theoretical attacks without a concrete exploit path
- Self-XSS or social-engineering attacks requiring user cooperation

## Supported Versions

Only the latest release line of this project receives security updates.
