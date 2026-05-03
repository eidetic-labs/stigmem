---
id: oidc-sso
title: OIDC / SSO Integration
sidebar_label: OIDC / SSO
---

# OIDC / SSO Integration

**Audience:** Node operators configuring identity federation for human users.

:::info Coming soon
This guide covers the OIDC identity bridge (B3, [ACM-82](/ACM/issues/ACM-82)). Implementation is in progress.
:::

The OIDC bridge maps human IdP identities (Google, GitHub, corporate SSO) to scoped stigmem API keys. When shipped, this guide will cover:
- Configuring your OIDC provider
- Mapping IdP claims to stigmem scopes
- Key rotation and expiry policy
