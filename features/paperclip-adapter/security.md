# Paperclip Adapter Security

The Paperclip adapter can write lifecycle and delegation facts from agent
workflows into Stigmem. Its security posture depends on least-privilege
Stigmem credentials, explicit source attribution, careful hook configuration,
and operator review before enabling automated writes.

## Security Posture

| Area | Current control | Evidence |
| --- | --- | --- |
| Credential handling | `STIGMEM_API_KEY` is read from the environment and sent as a bearer token when present. | `experimental/paperclip-adapter/emit-fact.js`; `experimental/paperclip-adapter/README.md` |
| Source attribution | `STIGMEM_SOURCE_ENTITY` supplies the source for asserted facts; the hook defaults to `agent:unknown` if unset. | `experimental/paperclip-adapter/hook.sh`; `experimental/paperclip-adapter/skill.md` |
| Hook opt-in | Hook execution requires explicit Paperclip or Claude Code hook wiring. | `experimental/paperclip-adapter/README.md`; `experimental/paperclip-adapter/concept.md` |
| Local heartbeat scope | `paperclip:last_active` is emitted with `local` scope. | `experimental/paperclip-adapter/hook.sh`; `docs/docs/spec/adapter-abi.md` |
| Silent skip when unconfigured | `hook.sh` exits without writing facts when `STIGMEM_URL` is absent. | `experimental/paperclip-adapter/hook.sh` |

## Security References

No dedicated R-* audit item is assigned to this adapter. The adapter intersects
with source attribution and federation concerns because automated agent hooks
can write facts under configured identities.

## Advisories and Findings

None currently recorded for the adapter.

## Residual Risk

- A misconfigured source entity can make agent writes harder to attribute.
- Overbroad Stigmem credentials can let automated hooks write beyond their
  intended scope.
- Federating Paperclip lifecycle facts without capability negotiation can expose
  relation namespaces to peers that do not understand them.
- Live Paperclip validation and dedicated hook tests are not complete.

## Operator Guidance

- Configure a distinct source entity for each agent or adapter identity.
- Use credentials scoped to the intended write surface.
- Keep `paperclip:last_active` local unless a future release line explicitly
  defines a broader sharing policy.
- Review hook commands before enabling automated writes in a Paperclip fleet.
