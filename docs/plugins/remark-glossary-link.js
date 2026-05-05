/**
 * Remark plugin that auto-links glossary terms to their definitions.
 *
 * On the first occurrence of each glossary term in a page's paragraph text,
 * the term is wrapped in a markdown link to /docs/reference/glossary#anchor.
 * Terms inside code blocks, headings, existing links, and the glossary page
 * itself are left untouched.
 */

const { visit } = require('unist-util-visit');

const GLOSSARY_TERMS = [
  { pattern: /\bCapability Token\b/i, anchor: 'capability-token', display: 'Capability Token' },
  { pattern: /\bCID\b/, anchor: 'cid', display: 'CID' },
  { pattern: /\bHLC\b/, anchor: 'hlc', display: 'HLC' },
  { pattern: /\bTombstone\b/i, anchor: 'tombstone', display: 'Tombstone' },
  { pattern: /\bSource Attestation\b/i, anchor: 'source-attestation', display: 'Source Attestation' },
  { pattern: /\bMemory Garden\b/i, anchor: 'garden', display: 'Memory Garden' },
];

function remarkGlossaryLink() {
  return (tree, file) => {
    const filePath = file?.history?.[0] ?? '';
    if (filePath.includes('reference/glossary')) return;

    const linked = new Set();

    visit(tree, 'text', (node, index, parent) => {
      if (!parent || parent.type === 'heading' || parent.type === 'link' || parent.type === 'code' || parent.type === 'inlineCode') {
        return;
      }

      for (const term of GLOSSARY_TERMS) {
        if (linked.has(term.anchor)) continue;

        const match = term.pattern.exec(node.value);
        if (!match) continue;

        const before = node.value.slice(0, match.index);
        const matched = match[0];
        const after = node.value.slice(match.index + matched.length);

        const linkNode = {
          type: 'link',
          url: '/docs/reference/glossary#' + term.anchor,
          children: [{ type: 'text', value: matched }],
        };

        const newNodes = [];
        if (before) newNodes.push({ type: 'text', value: before });
        newNodes.push(linkNode);
        if (after) newNodes.push({ type: 'text', value: after });

        parent.children.splice(index, 1, ...newNodes);
        linked.add(term.anchor);
        return index + newNodes.length;
      }
    });
  };
}

module.exports = remarkGlossaryLink;
