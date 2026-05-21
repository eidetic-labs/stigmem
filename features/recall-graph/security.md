# Recall Graph Security

## Threat Model Delta

Recall graph expands ordinary recall with graph traversal, embeddings, memory
cards, and derived context. That increases the blast radius of bad source
content, cloud embedding choices, garden-boundary mistakes, and write-back
loops from recalled data.

## Owned Risks

None currently identified. R-13 and R-20 remain unified threat-model entries
for embedding-provider exposure and embedding poisoning.

## Contributed Risks

| Risk | Contribution | Mitigation |
| --- | --- | --- |
| R-13 cloud embedding data exposure | Advanced recall can send fact content to opt-in cloud embedding providers. | Default to local embeddings; require operator data-classification review before cloud providers. |
| R-20 embedding poisoning | Adversarial vectors can manipulate recall ranking when cloud embeddings are enabled. | Treat cloud embedding as accepted operator risk and consider local re-embed sampling in future work. |
| R-21 agent feedback-loop worm | Graph recall can broaden the set of facts that influence an agent session. | Preserve session/provenance write boundaries and garden ACL checks across graph traversal. |

## Operator Scenarios

- Keep cloud embedding providers disabled unless data classification allows
  external processing.
- Treat graph-expanded recall as a broader influence set for provenance and
  write-back controls.
- Review garden ACL behavior before enabling cross-garden graph traversal.

## Conformance Pointers

Required vectors before promotion:

- graph traversal respects garden and scope boundaries;
- depth limits and cursor rules prevent traversal abuse;
- cloud embedding remains explicit opt-in;
- recalled graph provenance is preserved when agents write derived facts.

## Residual Risk

Advanced recall graph behavior should remain experimental until traversal
boundaries, embedding-provider posture, and provenance write-back controls have
promotion evidence.

## Advisories and Findings

No public GHSA is currently owned by this feature record.
