#!/usr/bin/env python3
"""Generate per-section spec pages from spec/stigmem-spec-v1.0.md and v1.1-draft.

Strategy (Option B+a from board):
- One page per top-level section number that's referenced in the docs.
- Pages contain the full markdown content from the source files (deltas as-is).
- Each top-level page has {#section-X}; each subsection heading gets {#section-X-Y}.
- For sections that don't exist in v1.0 or v1.1 source (e.g. §1, §4, §11, §12),
  emit a stub page with status + GitHub link.
- Mirror to versioned_docs/version-v1.1.
"""

from __future__ import annotations
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # repo root: <repo>/docs/scripts/<this-file>
# Permit override via argv
if len(sys.argv) > 1:
    ROOT = Path(sys.argv[1])

# v0.8-draft is the most recent self-contained spec covering §1–§16; v0.9 / v1.0 /
# v1.1-draft are deltas. Layer them all so each section page shows a base body
# (from v0.8 where present) plus any v0.9 / v1.0 / v1.1 additions.
SPEC_V08 = ROOT / 'spec/stigmem-spec-v0.8-draft.md'
SPEC_V09 = ROOT / 'spec/stigmem-spec-v0.9-draft.md'
SPEC_V10 = ROOT / 'spec/stigmem-spec-v1.0.md'
SPEC_V11 = ROOT / 'spec/stigmem-spec-v1.1-draft.md'
DOCS_CURRENT = ROOT / 'docs/docs/reference/spec'
DOCS_V11 = ROOT / 'docs/versioned_docs/version-v1.1/reference/spec'
UNIQUE_REFS = Path('/tmp/unique-refs.txt')

# Section metadata (status + one-line summary), mostly carried from previous heartbeat.
SECTION_INFO = {
    '1':  ('Motivation',                          'Stable (v1.0)',                         'Why immutable typed facts beat per-agent mutable stores.'),
    '2':  ('Atomic Fact Shape',                   'Stable (v1.0; v1.1 §2.8)',              'The fact tuple, value types, scopes, HLC, identity, federation-trust fields.'),
    '3':  ('Fact Semantics',                      'Stable (v1.0)',                         'Read/write semantics, retraction, contradiction, identity binding.'),
    '4':  ('Intent Envelope',                     'Stable (v1.0)',                         'Goal/constraint/preference/handoff envelope types for richer agent coordination.'),
    '5':  ('Wire Format',                         'Stable (v1.0; v1.1 §5.21–5.25)',         'JSON/HTTP wire format for facts, peers, gardens, trust manifests, and capability tokens.'),
    '6':  ('Federation',                          'Stable (v0.8 N-node)',                  'Peer handshake, pull replication, scope enforcement, conflict semantics, backpressure.'),
    '7':  ('Design Decisions Log',                'Stable',                                'Why the spec made the calls it did — federation, contradictions, entity-vs-agent scoping.'),
    '8':  ('Open Questions',                      'Living',                                'Currently-unresolved questions tracked in the spec for community feedback.'),
    '9':  ('Namespace Registry',                  'Stable',                                'Reserved relation prefixes (memory, system, stigmem, garden) and community registry process.'),
    '10': ('Schema and Migration',                'Stable',                                'SQL schema migrations 001-013 covering facts, federation, gardens, attestation, tombstones.'),
    '11': ('Failure Mode Scenarios',              'Stable',                                'Acceptance test scenarios — split-brain, malicious peer, partial failure, replay attack.'),
    '12': ('Adapter ABI',                         'Stable',                                'Minimum contract for platform adapters: env vars, assert/query, source binding.'),
    '14': ('Lint Semantics',                      'Stable',                                'POST /v1/lint — orphan relations, scope-escalation violations, contradiction surfacing.'),
    '15': ('Decay Semantics',                     'Stable',                                'Configurable TTL and confidence-decay policies; POST /v1/decay/sweep.'),
    '16': ('Synthesis',                           'Stable',                                'POST /v1/synthesis — confidence-weighted current-state snapshots per entity/scope.'),
    '17': ('Memory Garden',                       'Normative (v1.0)',                      "Named, ACL'd partitions of the fact store with admin/writer/reader role model."),
    '18': ('Source Attestation',                  'Normative (v1.0)',                      'API-key → entity_uri binding with enforce/warn/off modes; trust anchor for connectors.'),
    '19': ('Federation Trust',                    'Normative (v1.1)',                      'Org manifests, capability tokens, source-trust score, quarantine garden, recall-time sanitizer.'),
    '20': ('Recall & Graph',                      'Normative (v1.1)',                      'Graph adjacency index, vector embeddings, hybrid recall pipeline, memory cards, subscriptions, causal links.'),
    '21': ('Lazy Instruction Discovery',          'DRAFT normative (v1.1-draft, Phase 10)', 'Boot stub + manifest + on-demand recall for token-efficient agent instruction loading.'),
    '22': ('Security Hardening',                  'DRAFT normative (v1.1-draft, Phase 12)', 'mTLS federation, key rotation, audit log, per-principal quotas, container baseline.'),
    '23': ('Right-to-be-Forgotten Tombstones',    'DRAFT normative (v1.1-draft, Phase 13)', 'Cryptographic tombstones, recall-time suppression, federation propagation, legal-hold mode.'),
    '24': ('Time-Travel / As-Of Queries',         'DRAFT normative (v1.1-draft, Phase 13)', 'as_of parameter on /v1/recall and /v1/facts; append-only retraction log.'),
    '25': ('Content-Addressed Fact IDs',          'DRAFT normative (v1.1-draft, Phase 13)', 'SHA-256 CIDs for deduplication, tamper detection, dual UUID/CID addressing.'),
}

def slug_for_section(num: str) -> str:
    """Filename slug for top-level section X — used in URLs and sidebar.

    No leading number prefix because Docusaurus 3 strips them from the doc ID
    (it interprets ``N-``-prefixed filenames as sort hints and removes the
    prefix from the URL/ID), which would make sidebars + the remark plugin
    inconsistent.
    """
    if num not in SECTION_INFO:
        return f'section-{num}'
    title = SECTION_INFO[num][0]
    s = title.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip('-')
    return s


def parse_sections(path: Path) -> dict[str, str]:
    """Return {top_level_num: full_section_markdown} from a spec file.

    A section spans from ``## N. ...`` up to the next ``## M. ...`` or EOF.
    """
    if not path.exists():
        return {}
    text = path.read_text()
    lines = text.splitlines()
    sections: dict[str, list[str]] = {}
    current_num: str | None = None
    current_lines: list[str] = []
    h2_re = re.compile(r'^## (\d+)\.\s+(.+)$')
    for line in lines:
        m = h2_re.match(line)
        if m:
            if current_num is not None:
                sections.setdefault(current_num, []).extend(current_lines + [''])
            current_num = m.group(1)
            current_lines = [line]
        elif current_num is not None:
            current_lines.append(line)
    if current_num is not None:
        sections.setdefault(current_num, []).extend(current_lines)
    return {k: '\n'.join(v).rstrip() + '\n' for k, v in sections.items()}


def annotate_subsection_anchors(body: str, top_num: str) -> str:
    """Add ``{#section-X-Y[-Z]}`` to ``### N.M[.K] Title`` style headings.

    Only annotates headings whose number matches the page's top-level section.
    """
    out = []
    sub_re = re.compile(r'^(#{2,5})\s+(\d+(?:\.\d+)*)\s+(.+?)\s*$')
    for line in body.splitlines():
        m = sub_re.match(line)
        if m:
            depth = m.group(1)
            num = m.group(2)
            rest = m.group(3).rstrip()
            if num == top_num:
                # Top heading itself — anchor as section-X
                if not rest.endswith('}'):
                    line = f'{depth} §{num}. {rest} {{#section-{num}}}'
            elif num.startswith(top_num + '.'):
                slug = num.replace('.', '-')
                if '{#section-' not in rest:
                    line = f'{depth} §{num} {rest} {{#section-{slug}}}'
        out.append(line)
    return '\n'.join(out)


REPO_BASE = 'https://github.com/Eidetic-Labs/stigmem/blob/main'

def rewrite_relative_links(body: str) -> str:
    """Repoint repo-relative links in spec source to their GitHub canonical URL.

    The spec markdown sits in ``spec/`` so it uses ``../SECURITY.md`` style links
    that don't resolve once we render the body inside ``docs/reference/spec/``.
    """
    body = re.sub(r'\]\(\.\./SECURITY\.md(#[^)]*)?\)', lambda m: f']({REPO_BASE}/SECURITY.md{m.group(1) or ""})', body)
    body = re.sub(r'\]\(\.\./CONTRIBUTING\.md(#[^)]*)?\)', lambda m: f']({REPO_BASE}/CONTRIBUTING.md{m.group(1) or ""})', body)
    body = re.sub(r'\]\(\.\./README\.md(#[^)]*)?\)', lambda m: f']({REPO_BASE}/README.md{m.group(1) or ""})', body)
    return body


def _strip_h2_header(body: str) -> str:
    lines = body.splitlines()
    if lines and lines[0].startswith('## '):
        lines = lines[1:]
    return '\n'.join(lines).strip()


# Parses ``### N.M[.K] Title`` style subsection headings within a section body.
# We use the matching depth (### / #### / #####) to render at the right h-level
# in the output.
SUBSECTION_HEADING_RE = re.compile(r'^(#{3,5})\s+(\d+(?:\.\d+)*)\s+(.+?)\s*$')


def split_section_into_chunks(body: str, top_num: str) -> list[tuple[str, str]]:
    """Split a section body into ordered ``(key, text)`` chunks.

    A ``key`` is either ``_intro`` for content before the first subsection
    heading, or a subsection number like ``2.7``. The chunk text includes its
    own heading line so the renderer can preserve depth.
    """
    chunks: list[tuple[str, str]] = []
    current_key: str | None = '_intro'
    current_lines: list[str] = []
    for line in body.splitlines():
        m = SUBSECTION_HEADING_RE.match(line)
        if m:
            num = m.group(2)
            # Only treat as a subsection split if the number is under our top section.
            if num == top_num or num.startswith(top_num + '.'):
                if current_key is not None and current_lines:
                    chunks.append((current_key, '\n'.join(current_lines).rstrip()))
                current_key = num
                current_lines = [line]
                continue
        current_lines.append(line)
    if current_key is not None and current_lines:
        chunks.append((current_key, '\n'.join(current_lines).rstrip()))
    # Drop empty intro
    chunks = [(k, t) for (k, t) in chunks if t.strip()]
    return chunks


def _sort_key_for(num: str) -> tuple:
    """Sort key — _intro first, then numeric ascending by tuple of ints."""
    if num == '_intro':
        return (0,)
    return (1,) + tuple(int(p) for p in num.split('.'))


def _normalize(text: str) -> str:
    """Whitespace-collapsed normalization for revision deduplication."""
    return re.sub(r'\s+', ' ', text).strip()


def render_subsection_with_revisions(
    sub_num: str,
    versions: list[tuple[str, str]],
    top_num: str,
) -> str:
    """Render one subsection: latest version visible, older revisions in a
    collapsed ``<details>`` block beneath. ``versions`` is oldest-to-newest.
    """
    latest_label, latest_text = versions[-1]
    latest_norm = _normalize(latest_text)
    # Drop older revisions whose text is identical to the latest (no real change).
    distinct_older = [
        (label, text) for (label, text) in versions[:-1]
        if _normalize(text) != latest_norm and text.strip()
    ]
    rendered_latest = annotate_subsection_anchors(rewrite_relative_links(latest_text), top_num)
    out = [rendered_latest]
    if distinct_older:
        out.append('')
        out.append('<details>')
        older_labels = ', '.join(v[0].replace('stigmem-spec-', '').replace('.md', '') for v in distinct_older)
        latest_short = latest_label.replace('stigmem-spec-', '').replace('.md', '')
        out.append(f'<summary>Revisions before {latest_short}: {older_labels}</summary>')
        out.append('')
        for older_label, older_text in distinct_older:
            out.append(f'**From `{older_label}`:**')
            out.append('')
            out.append(rewrite_relative_links(older_text))
            out.append('')
        out.append('</details>')
    return '\n'.join(out).rstrip()


def merge_sections(top_num: str, sources: list[tuple[str, dict[str, str]]]) -> str | None:
    """Build the per-section page body by deduplicating at the subsection level.

    Strategy (Option B from board):
      1. For each source that contains §top_num, parse the body into ordered
         (subsection_num | _intro, text) chunks.
      2. Build a {subsection_num: [(source_label, text), ...]} map ordered by
         source age (oldest first).
      3. Render subsections in strict numeric order. For each, show only the
         most-recent source's text. If older sources contributed text to the
         same subsection, append a collapsed ``<details>`` accordion of the
         older revisions.

    Sections with content from a single source render as plain text (no accordion).
    """
    # Collect per-subsection version chains
    sub_versions: dict[str, list[tuple[str, str]]] = {}
    for label, src in sources:
        if top_num not in src:
            continue
        body = _strip_h2_header(src[top_num])
        chunks = split_section_into_chunks(body, top_num)
        for sub_num, chunk_text in chunks:
            sub_versions.setdefault(sub_num, []).append((label, chunk_text))
    if not sub_versions:
        return None

    # Render in numeric order. Skip subsections whose latest contributing text
    # is empty (e.g. an `_intro` that's just the section heading).
    rendered: list[str] = []
    for sub_num in sorted(sub_versions.keys(), key=_sort_key_for):
        versions = sub_versions[sub_num]
        if not versions[-1][1].strip():
            continue
        rendered.append(render_subsection_with_revisions(sub_num, versions, top_num))
        rendered.append('')
    return '\n'.join(rendered).rstrip() + '\n' if rendered else None


def collect_referenced_subsections(top_num: str) -> list[str]:
    """Return all subsection refs (e.g. ``2.1``, ``19.3.4``) under ``top_num``."""
    subs = []
    if UNIQUE_REFS.exists():
        for raw in UNIQUE_REFS.read_text().splitlines():
            r = raw.strip().lstrip('§')
            if not r or '.' not in r:
                continue
            if r.split('.')[0] == top_num:
                subs.append(r)
    # de-dupe, preserve numeric order
    seen = set()
    out = []
    for r in sorted(subs, key=lambda s: tuple(int(p) for p in s.split('.'))):
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def append_missing_subsection_anchors(body: str | None, top_num: str) -> str:
    """Ensure every referenced subsection anchor exists on the page, even when
    the spec source markdown doesn't contain that subsection heading directly."""
    subs = collect_referenced_subsections(top_num)
    if not subs:
        return body or ''
    existing = set()
    if body:
        # Anchors already injected by ``annotate_subsection_anchors``.
        existing = set(re.findall(r'\{#(section-[\d-]+)\}', body))
    missing = [s for s in subs if f'section-{s.replace(".", "-")}' not in existing]
    if not missing:
        return body or ''
    out = (body or '').rstrip() + '\n\n## Subsection anchors {#subsection-anchors}\n\n'
    out += '*Anchors below are provided so docs links to specific subsections always resolve, even when the subsection text lives only in earlier spec drafts.*\n\n'
    for s in missing:
        slug = s.replace('.', '-')
        out += f'### §{s} {{#section-{slug}}}\n\n'
    return out


def page_for_section(top_num: str, body: str | None) -> str:
    title, status, summary = SECTION_INFO.get(top_num, (f'Section {top_num}', 'Unknown', ''))
    spec_file = 'stigmem-spec-v1.0.md' if int(top_num) <= 18 else 'stigmem-spec-v1.1-draft.md'
    out = []
    out.append('---')
    # Don't set id explicitly — let Docusaurus auto-derive from file path so the
    # sidebar entries (e.g. "reference/spec/19-federation-trust") resolve.
    out.append(f'title: §{top_num}. {title}')
    out.append(f'sidebar_label: §{top_num} {title}')
    out.append('audience: Spec')
    desc = (summary or '').replace('"', "'")
    out.append(f'description: "Stigmem spec section {top_num} — {desc}"')
    out.append('---')
    out.append('')
    out.append(f'# §{top_num}. {title} {{#section-{top_num}}}')
    out.append('')
    out.append(f'**Status:** {status}')
    out.append('')
    out.append(summary)
    out.append('')
    out.append(f'**Authoritative source:** [`spec/{spec_file}`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/{spec_file})')
    out.append('')
    if body:
        out.append(':::note Section body')
        out.append('Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.')
        out.append(':::')
        out.append('')
        out.append(body)
    else:
        out.append(':::note Stub')
        out.append(f'§{top_num} predates the v1.0 / v1.1-draft source files in this repo. The current self-contained text for this section lives in earlier spec drafts (e.g. `stigmem-spec-v0.5-draft.md`, `stigmem-spec-v0.7-draft.md`). Follow the GitHub link above and walk back through the version chain in `spec/` for the full historical text.')
        out.append(':::')
    rendered = '\n'.join(out).rstrip() + '\n'
    rendered = append_missing_subsection_anchors(rendered, top_num)
    return rendered


def main():
    v08 = parse_sections(SPEC_V08)
    v09 = parse_sections(SPEC_V09)
    v10 = parse_sections(SPEC_V10)
    v11 = parse_sections(SPEC_V11)
    sources = [
        ('stigmem-spec-v0.8-draft.md', v08),
        ('stigmem-spec-v0.9-draft.md', v09),
        ('stigmem-spec-v1.0.md',       v10),
        ('stigmem-spec-v1.1-draft.md', v11),
    ]

    # Build the union of top-level sections we need pages for.
    refs_in_docs: set[str] = set()
    if UNIQUE_REFS.exists():
        for line in UNIQUE_REFS.read_text().splitlines():
            line = line.strip().lstrip('§')
            if not line:
                continue
            top = line.split('.')[0]
            if top.isdigit() and 1 <= int(top) <= 30:
                refs_in_docs.add(top)
    needed = refs_in_docs | set(SECTION_INFO.keys()) | set(v08.keys()) | set(v09.keys()) | set(v10.keys()) | set(v11.keys())

    section_to_slug: dict[str, str] = {}
    written = 0
    stubs = 0

    # Write pages
    for top in sorted(needed, key=int):
        slug = slug_for_section(top)
        section_to_slug[top] = slug
        body = merge_sections(top, sources)
        if body is None:
            stubs += 1
        page_md = page_for_section(top, body)
        for dest_dir in [DOCS_CURRENT, DOCS_V11]:
            dest_dir.mkdir(parents=True, exist_ok=True)
            (dest_dir / f'{slug}.md').write_text(page_md)
        written += 1

    # Index page — short navigator listing each section page with status.
    idx = []
    idx.append('---')
    idx.append('id: index')
    idx.append('title: Specification')
    idx.append('sidebar_label: Overview')
    idx.append('audience: Spec')
    idx.append('description: Stigmem protocol specification — section navigator. Each row links to the full section page.')
    idx.append('---')
    idx.append('')
    idx.append('# Stigmem Protocol Specification')
    idx.append('')
    idx.append(':::note Authoritative source')
    idx.append('Spec source markdown lives in [`spec/stigmem-spec-v1.0.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/stigmem-spec-v1.0.md) and [`spec/stigmem-spec-v1.1-draft.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/stigmem-spec-v1.1-draft.md). Each section below renders the source text inline; sections marked stub have content only in earlier spec drafts and link to GitHub for the full history.')
    idx.append(':::')
    idx.append('')
    idx.append(':::info Security disclosure')
    idx.append('Report vulnerabilities via the [GitHub private advisory path](https://github.com/eidetic-labs/stigmem/security/advisories) — not as public issues. See [SECURITY.md](https://github.com/eidetic-labs/stigmem/blob/main/SECURITY.md) for the full coordinated-disclosure policy.')
    idx.append(':::')
    idx.append('')
    idx.append('## Sections')
    idx.append('')
    idx.append('| Section | Status | Summary |')
    idx.append('|---------|--------|---------|')
    for top in sorted(needed, key=int):
        if top not in SECTION_INFO:
            continue
        title, status, summary = SECTION_INFO[top]
        slug = section_to_slug[top]
        has_content = top in v08 or top in v09 or top in v10 or top in v11
        marker = '' if has_content else ' *(stub)*'
        idx.append(f'| [§{top}. {title}](./{slug}){marker} | {status} | {summary} |')
    idx.append('')

    idx_text = '\n'.join(idx) + '\n'
    for dest_dir in [DOCS_CURRENT, DOCS_V11]:
        (dest_dir / 'index.md').write_text(idx_text)

    # Section-to-slug map for the remark plugin
    map_path = ROOT / 'docs/plugins/spec-section-map.json'
    map_path.write_text(json.dumps(section_to_slug, indent=2, sort_keys=False) + '\n')

    print(f'Wrote {written} per-section pages ({stubs} stubs) to {DOCS_CURRENT} and {DOCS_V11}.')
    print(f'Wrote section-to-slug map to {map_path}.')


if __name__ == '__main__':
    main()
