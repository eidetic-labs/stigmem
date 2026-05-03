# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.x     | Yes       |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Please report security issues via GitHub's private advisory path:

1. Go to the [Security Advisories](https://github.com/eidetic-labs/stigmem/security/advisories) page.
2. Click **"Report a vulnerability"**.
3. Fill in the details: description, reproduction steps, potential impact, and suggested fix if known.

We will acknowledge your report within **48 hours** and aim to release a patch within **14 days** for critical vulnerabilities.

## Scope

In-scope:
- Remote code execution or injection vulnerabilities
- Authentication or authorization bypasses
- Data exposure or exfiltration
- Supply chain attacks on our published packages

Out-of-scope:
- Issues in third-party dependencies (report to the upstream project)
- Rate limiting or resource exhaustion without a clear security impact

## Disclosure Policy

We follow coordinated disclosure. We ask reporters to give us 90 days before public disclosure, except for issues already being actively exploited in the wild.
