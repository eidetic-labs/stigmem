/**
 * Remark plugin that converts bare `§X.Y[.Z]` spec-section references in
 * prose into markdown links pointing at the matching per-section spec page,
 * e.g. /docs/reference/spec/19-federation-trust#section-19-3.
 *
 * - Only matches refs whose top-level number is 1–30 (so unrelated citations
 *   like California Civil Code §1798.105 are left alone) AND whose top-level
 *   number maps to a known section page (per spec-section-map.json).
 * - Skips text inside headings, existing links, code blocks, and inline code.
 * - Skips the spec subtree itself (no self-linking).
 */

const { visit } = require('unist-util-visit');
const SECTION_MAP = require('./spec-section-map.json');

const SPEC_REF = /§(\d{1,2}(?:\.\d+)*)\b/g;

function refToTarget(ref) {
  const top = ref.split('.')[0];
  const slug = SECTION_MAP[top];
  if (!slug) return null;
  if (ref === top) {
    // §X — link to the section page top.
    return `/docs/reference/spec/${slug}`;
  }
  // §X.Y[.Z] — link to the matching subsection anchor on the per-section page.
  const anchor = 'section-' + ref.replace(/\./g, '-');
  return `/docs/reference/spec/${slug}#${anchor}`;
}

function remarkSpecLink() {
  return (tree, file) => {
    const filePath = file?.history?.[0] ?? '';
    if (filePath.includes('reference/spec/')) return;

    visit(tree, 'text', (node, index, parent) => {
      if (!parent) return;
      if (
        parent.type === 'heading' ||
        parent.type === 'link' ||
        parent.type === 'linkReference' ||
        parent.type === 'code' ||
        parent.type === 'inlineCode' ||
        parent.type === 'definition'
      ) {
        return;
      }

      const value = node.value;
      if (!value || !value.includes('§')) return;

      const matches = [...value.matchAll(SPEC_REF)];
      if (matches.length === 0) return;

      const valid = matches
        .map((m) => ({ m, target: refToTarget(m[1]) }))
        .filter((x) => x.target !== null);
      if (valid.length === 0) return;

      const newNodes = [];
      let cursor = 0;
      for (const { m, target } of valid) {
        const start = m.index;
        const end = start + m[0].length;
        if (start > cursor) {
          newNodes.push({ type: 'text', value: value.slice(cursor, start) });
        }
        newNodes.push({
          type: 'link',
          url: target,
          title: null,
          children: [{ type: 'text', value: m[0] }],
        });
        cursor = end;
      }
      if (cursor < value.length) {
        newNodes.push({ type: 'text', value: value.slice(cursor) });
      }

      parent.children.splice(index, 1, ...newNodes);
      return index + newNodes.length;
    });
  };
}

module.exports = remarkSpecLink;
