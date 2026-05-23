# Memory Garden Advanced ACL Security

## Threat Model Delta

Memory Garden advanced ACL can narrow or widen the R-21 feedback-loop risk
depending on its final design. A hardened design should make session read/write
boundaries explicit and auditable. A loose design could authorize an agent to
write back into the same garden that supplied prompt-influencing facts.

## Owned Risks

None currently identified. Any future owned R-XX risk must be added to the
unified threat model and this feature record in the same PR.

## Contributed Risks

| Risk | Contribution | Mitigation |
| --- | --- | --- |
| R-21 agent feedback-loop worm | Garden ACLs are one candidate boundary for preventing write-back into scopes or gardens that influenced the same agent session. | Treat advanced ACL as incomplete until same-session read/write graph isolation and audit evidence are validated. |

## Operator Scenarios

- Memory Garden ACL is opt-in. Default deployments enforce direct `garden_id`
  reads and writes through the core guards, but tenant-wide queries, recall
  ranking, push subscriptions, OIDC permission ceilings, and graph traversal
  do not filter by garden membership unless `stigmem-plugin-memory-garden-acl`
  is registered and the relevant `STIGMEM_MEMORY_GARDEN_ACL_*` flags are
  enabled.
- `/v1/doctor` is unauthenticated in v0.9.0a6 and returns the coarse
  `memory_garden_acl_filtering` posture to any HTTP caller. This is accepted
  for the alpha as standard ops-endpoint disclosure because it does not expose
  garden names, membership rows, tenant identifiers, or policy subjects.
  Future hardening options are to auth-gate `/v1/doctor` entirely or suppress
  the posture field for anonymous callers.
- Quarantine moderation keeps a separate node-admin override. Node-admin bypass is intentional.
  Node admins are the system's last-resort moderation authority.
  Garden-scoped moderators must still hold `quarantine:moderator` or `admin`
  role in the specific quarantine garden.
- Do not treat garden ACLs as a complete R-21 mitigation until per-session
  read/write graph isolation is designed and tested.
- Review any feature design that grants writer keys based on recent recall
  context as security-sensitive.

## Conformance Pointers

Required adversarial vectors before promotion:

- an agent cannot write into a garden it read from in the same protected
  session;
- attempted graph-isolation bypasses leave audit evidence;
- outbound federation excludes facts derived from transitively recalled
  content until explicitly approved.

## Residual Risk

Gate 1 remains partial. The a6 disposition is that Memory Garden advanced ACL
supports and coexists with R-21 mitigation work by providing an opt-in
membership boundary for assertion, recall, graph, OIDC, and subscription
surfaces. It does not, by itself, implement or close R-21 same-session
read/write graph isolation. R-21 closure still requires session, graph, and
audit evidence outside this feature boundary.

## Advisories and Findings

No public GHSA is currently owned by this feature record.
