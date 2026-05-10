---
title: Human Surface (Web UI)
sidebar_label: Human Surface (Web UI)
audience: Integrator
---

# Human Surface (Web UI)

**Audience:** Curators, contributors, and consumers who interact with a Stigmem node via a browser rather than the API directly.

The Web UI is a single-page application served by the node at `/ui`. It is built with Alpine.js and Tailwind CSS (both loaded from CDN — no separate build step or install required). All actions map directly to the REST API; anything you do in the UI you can reproduce with `curl`.

## Quick start

1. Navigate to `http://<node-host>:8000/ui`.
2. Enter your node's base URL and your API key in the **Connection** bar at the top, then click **Connect**.
3. The header confirms your identity (`Signed in as <entity_uri>`) and shows your permission badges.

Your credentials are saved in `localStorage` (`sm_url` / `sm_key`) so you do not need to re-enter them on reload.

:::info Obtaining an API key
Use the [OIDC / SSO](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/oidc-sso) exchange flow if your organisation runs an IdP, or ask your node operator to provision a static key. See [Authentication](./authentication) for the full key model.
:::

## Personas and roles

| Role | Description | What they can do in the UI |
|------|-------------|---------------------------|
| **Curator** | Garden admin; approves contested facts | All tabs; retract any fact; manage garden members and roles |
| **Contributor** | Write access to one or more gardens | Facts, Assert, Audit Log tabs; retract own facts |
| **Consumer** | Read-only | Facts and Audit Log tabs; no Assert or retract |

The UI detects your role from `GET /v1/me` — write controls are hidden or disabled if your key lacks the `write` permission.

## Tabs

### Facts

Browse and search the fact store.

**Filters:**

| Filter | Description |
|--------|-------------|
| Entity URI | Exact or prefix match on `entity` |
| Relation | Exact match on `relation` |
| Scope | Dropdown: `local`, `team`, `company`, `public` |
| Source | Exact match on `source` |
| Min confidence | Numeric 0–1 (default: no filter) |
| Include contradicted | Checkbox; off by default |

Results are paginated. The **Load more** button appends the next page.

**Columns:** Entity, Relation, Value, Scope (badge), Confidence, Timestamp, Status (conflicted / retracted), Actions.

**Actions per row:**
- **Detail** — Opens a modal with all fields including `id`, `valid_until`, and HLC.
- **Retract** — Opens a confirmation modal with an optional reason field. Sends `POST /v1/facts` with `confidence: 0`; the reason is stored as a `stigmem:retract:reason` fact keyed on the retracted fact's ID.

### Assert

Create new facts manually.

| Field | Notes |
|-------|-------|
| Entity URI | Required; free-text |
| Relation | Required; should follow namespace registry (§9) |
| Value type | Selector: `string`, `text`, `number`, `boolean`, `datetime`, `ref`, `null` |
| Value | Input adapts to the selected type |
| Source URI | Required; pre-filled from `GET /v1/me` if you are authenticated |
| Scope | Selector: `local`, `team`, `company`, `public` |
| Confidence | Slider 0–1 (default: 1.0) |
| Valid until | Optional ISO 8601 timestamp |

On submit, the response shows the new fact ID and warns if the assertion contradicts an existing fact.

### Audit Log

A chronological view of all fact mutations, including retractions and contradictions.

**Filters:** Source URI (`My assertions` pre-fill button), Entity, Scope, Include contradicted.

Useful for compliance reviews and debugging — equivalent to `GET /v1/facts?include_contradicted=true&order=hlc_desc`.

### Gardens

Manage memory gardens (named, ACL-controlled partitions above scope — see spec §17).

**List view:** Cards show slug, display name, scope badge, and creation time. Click a card to open the detail view.

**Detail view:**

| Section | Description |
|---------|-------------|
| Garden info | slug, display name, description, `garden_id` (UUID), `created_by` |
| Members table | Entity URI, Role (editable dropdown for admins), Added by, Added at, Remove button |
| Add Member button | Modal: entity URI + role selector (`admin`, `writer`, `reader`) |
| Browse facts link | Opens Facts tab pre-filtered to this garden's scope |

**Create garden:** Click **+ New Garden**. Provide a slug (lowercase alphanumeric + hyphens, 1–64 chars), display name, scope, and optional description. The creator is automatically added as `admin`.

**Role management:** Admins can change any member's role via the dropdown in the members table. The last admin cannot be demoted or removed (the node returns `403`).

## API endpoints called

Every UI action maps to a REST endpoint:

| UI action | Endpoint |
|-----------|----------|
| Connect / check identity | `GET /v1/me` |
| Facts tab query | `GET /v1/facts?{filters}` |
| Assert a fact | `POST /v1/facts` |
| Retract a fact | `POST /v1/facts` with `confidence: 0` + reason fact |
| Audit Log query | `GET /v1/facts?include_contradicted=true` |
| List gardens | `GET /v1/gardens` |
| Garden detail | `GET /v1/gardens/{slug}` |
| Create garden | `POST /v1/gardens` |
| Delete garden | `DELETE /v1/gardens/{slug}` |
| List members | `GET /v1/gardens/{slug}/members` |
| Add member | `POST /v1/gardens/{slug}/members` |
| Change role | `PATCH /v1/gardens/{slug}/members/{entity_uri}` |
| Remove member | `DELETE /v1/gardens/{slug}/members/{entity_uri}` |

## See also

- [OIDC / SSO Integration](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/oidc-sso) — how to sign in via your organisation's IdP instead of a static key
- [Authentication](./authentication) — full API key and permission model
- [Asserting Facts](../concepts/facts/asserting-facts) — `curl` examples for the same operations
- [Gardens API](../concepts/facts/asserting-facts) — spec §17 for the data model behind the Gardens tab
