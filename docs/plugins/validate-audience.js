const VALID_AUDIENCES = ['Operator', 'Integrator', 'Spec'];

// Audience badges are only meaningful where the page's audience is non-obvious from
// its top-level section. The Learn section name already implies a general reader, so
// pages under learn/ (and a few catch-all sections) opt out of the audience requirement.
const AUDIENCE_OPTIONAL_PREFIXES = ['learn/', 'community/', 'reference/glossary'];

module.exports = function validateAudiencePlugin() {
  return {
    name: 'validate-audience',
    async allContentLoaded({allContent}) {
      const docsPlugin = allContent['docusaurus-plugin-content-docs']?.default;
      if (!docsPlugin) return;

      const errors = [];
      for (const version of docsPlugin.loadedVersions ?? []) {
        for (const doc of version.docs ?? []) {
          if (doc.sourceDirName?.includes('reference/api/generated')) {
            continue;
          }
          const isOptional = AUDIENCE_OPTIONAL_PREFIXES.some(
            (prefix) => doc.sourceDirName?.startsWith(prefix) || doc.id?.startsWith(prefix)
          );
          const audience = doc.frontMatter?.audience;
          if (!audience) {
            if (!isOptional) {
              errors.push(`${doc.id}: missing "audience" frontmatter`);
            }
          } else if (!VALID_AUDIENCES.includes(audience)) {
            errors.push(`${doc.id}: invalid audience "${audience}" (must be one of ${VALID_AUDIENCES.join(', ')})`);
          }
        }
      }

      if (errors.length > 0) {
        throw new Error(
          `[validate-audience] ${errors.length} doc(s) missing or invalid "audience" frontmatter:\n` +
          errors.map(e => `  - ${e}`).join('\n')
        );
      }
    },
  };
};
