// @ts-check
const { themes: prismThemes } = require('prism-react-renderer');
const remarkGlossaryLink = require('./plugins/remark-glossary-link');
const remarkSpecLink = require('./plugins/remark-spec-link');

// RTD serves the site under /<language>/<version>/ in multi-version mode.
// Use injected env vars so asset paths resolve correctly without changing local dev.
const baseUrl = process.env.READTHEDOCS === 'True'
  ? `/${process.env.READTHEDOCS_LANGUAGE}/${process.env.READTHEDOCS_VERSION}/`
  : '/';

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Stigmem Protocol',
  tagline: 'Structured, federated knowledge graph for AI agents',
  favicon: 'img/favicon.ico',

  url: 'https://docs.stigmem.dev',
  baseUrl,

  onBrokenLinks: 'throw',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  markdown: {
    mermaid: true,
    hooks: {
      onBrokenMarkdownLinks: 'warn',
    },
  },

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: './sidebars.js',
          docItemComponent: '@theme/ApiItem',
          remarkPlugins: [remarkGlossaryLink, remarkSpecLink],
          lastVersion: 'v1.1',
          versions: {
            current: {
              label: 'v2.0-draft',
              path: 'next',
              badge: true,
              banner: 'unreleased',
            },
            'v1.1': { label: 'v1.1', badge: true },
            'v0.2': { label: 'v0.2', path: 'v0.2', badge: true },
          },
        },
        blog: {
          showReadingTime: true,
          blogTitle: 'Stigmem Blog',
          blogDescription: 'Updates, announcements, and deep-dives from the Stigmem project.',
          postsPerPage: 10,
          blogSidebarTitle: 'Recent posts',
          blogSidebarCount: 5,
        },
        theme: {
          customCss: './src/css/custom.css',
        },
      }),
    ],
  ],

  plugins: [
    [
      'docusaurus-plugin-openapi-docs',
      {
        id: 'api',
        docsPluginId: 'classic',
        config: {
          stigmem: {
            specPath: './openapi/stigmem.json',
            outputDir: 'docs/reference/api/generated',
            downloadUrl: './openapi/stigmem.json',
            sidebarOptions: {
              groupPathsBy: 'tag',
              categoryLinkSource: 'tag',
            },
          },
        },
      },
    ],
    [
      '@easyops-cn/docusaurus-search-local',
      /** @type {import("@easyops-cn/docusaurus-search-local").PluginOptions} */
      ({
        hashed: true,
        indexPages: true,
      }),
    ],
    require.resolve('./plugins/validate-audience'),
    [
      '@docusaurus/plugin-client-redirects',
      {
        redirects: [
          // --- learn/ (was about/, getting-started/) ---
          { from: '/docs/about/memory-garden', to: '/docs/learn/concepts/memory-garden' },
          { from: '/docs/about/security', to: '/docs/community/security-disclosure' },
          { from: '/docs/about/state-of-stigmem', to: '/docs/learn/features' },
          { from: '/docs/getting-started/installation', to: '/docs/learn/quickstart/installation' },
          { from: '/docs/getting-started/quickstart', to: '/docs/learn/quickstart/quickstart-tutorial' },
          { from: '/docs/getting-started/upgrade-v1', to: '/docs/learn/quickstart/upgrade-v1' },

          // --- build/ (was guides/, sdks/, tutorials/) ---
          { from: '/docs/guides', to: '/docs/build/guides' },
          { from: '/docs/guides/agent-keypairs', to: '/docs/build/guides/agent-keypairs' },
          { from: '/docs/guides/asserting-facts', to: '/docs/build/guides/asserting-facts' },
          { from: '/docs/guides/async-jobs', to: '/docs/build/guides/async-jobs' },
          { from: '/docs/guides/audit-log', to: '/docs/build/guides/audit-log' },
          { from: '/docs/guides/authentication', to: '/docs/build/guides/authentication' },
          { from: '/docs/guides/backup-restore', to: '/docs/operate/runbooks/backup-restore' },
          { from: '/docs/guides/billing-hooks', to: '/docs/build/guides/billing-hooks' },
          { from: '/docs/guides/conflict-resolution', to: '/docs/build/guides/conflict-resolution' },
          { from: '/docs/guides/conformance', to: '/docs/build/guides/conformance' },
          { from: '/docs/guides/content-addressing', to: '/docs/build/guides/content-addressing' },
          { from: '/docs/guides/cursor-reset-recovery', to: '/docs/operate/runbooks/cursor-reset-recovery' },
          { from: '/docs/guides/decay', to: '/docs/build/guides/decay' },
          { from: '/docs/guides/design-partner-notes', to: '/docs/build/guides/design-partner-notes' },
          { from: '/docs/guides/embeddings', to: '/docs/build/guides/embeddings' },
          { from: '/docs/guides/encryption-at-rest', to: '/docs/build/guides/encryption-at-rest' },
          { from: '/docs/guides/federation-4node', to: '/docs/build/guides/federation-4node' },
          { from: '/docs/guides/federation-trust', to: '/docs/build/guides/federation-trust' },
          { from: '/docs/guides/federation', to: '/docs/build/guides/federation' },
          { from: '/docs/guides/fuzzy-entity-resolver', to: '/docs/build/guides/fuzzy-entity-resolver' },
          { from: '/docs/guides/human-key-issuance', to: '/docs/build/guides/human-key-issuance' },
          { from: '/docs/guides/human-surface', to: '/docs/build/guides/human-surface' },
          { from: '/docs/guides/instruction-migration', to: '/docs/build/guides/instruction-migration' },
          { from: '/docs/guides/intent-envelopes', to: '/docs/build/guides/intent-envelopes' },
          { from: '/docs/guides/lazy-instructions', to: '/docs/build/guides/lazy-instructions' },
          { from: '/docs/guides/libsql-pitr', to: '/docs/build/guides/libsql-pitr' },
          { from: '/docs/guides/memory-cards', to: '/docs/build/guides/memory-cards' },
          { from: '/docs/guides/memory-gardens', to: '/docs/build/guides/memory-gardens' },
          { from: '/docs/guides/multi-tenancy', to: '/docs/build/guides/multi-tenancy' },
          { from: '/docs/guides/multi-tenant', to: '/docs/build/guides/multi-tenancy' },
          { from: '/docs/guides/oidc-sso', to: '/docs/build/guides/oidc-sso' },
          { from: '/docs/guides/python-sdk', to: '/docs/build/sdks/python' },
          { from: '/docs/guides/querying-facts', to: '/docs/build/guides/querying-facts' },
          { from: '/docs/guides/recall', to: '/docs/build/guides/recall' },
          { from: '/docs/guides/relay-backpressure', to: '/docs/build/guides/relay-backpressure' },
          { from: '/docs/guides/rtbf', to: '/docs/build/guides/rtbf' },
          { from: '/docs/guides/scope-propagation', to: '/docs/build/guides/scope-propagation' },
          { from: '/docs/guides/source-attestation', to: '/docs/build/guides/source-attestation' },
          { from: '/docs/guides/subscriptions', to: '/docs/build/guides/subscriptions' },
          { from: '/docs/guides/synthesis', to: '/docs/build/guides/synthesis' },
          { from: '/docs/guides/time-travel', to: '/docs/build/guides/time-travel' },
          { from: '/docs/guides/connectors', to: '/docs/build/connectors' },
          { from: '/docs/guides/connectors/codex-cli', to: '/docs/build/connectors/codex-cli' },
          { from: '/docs/guides/connectors/continue-dev', to: '/docs/build/connectors/continue-dev' },
          { from: '/docs/guides/connectors/cursor', to: '/docs/build/connectors/cursor' },
          { from: '/docs/guides/connectors/gemini', to: '/docs/build/connectors/gemini' },
          { from: '/docs/guides/connectors/obsidian-plugin', to: '/docs/build/connectors/obsidian-plugin' },
          { from: '/docs/guides/connectors/obsidian', to: '/docs/build/connectors/obsidian' },
          { from: '/docs/guides/connectors/ollama-litellm', to: '/docs/build/connectors/ollama-litellm' },
          { from: '/docs/guides/connectors/openclaw', to: '/docs/build/connectors/openclaw' },
          { from: '/docs/guides/connectors/paperclip-federation', to: '/docs/build/connectors/paperclip-federation' },
          { from: '/docs/guides/connectors/paperclip', to: '/docs/build/connectors/paperclip' },
          { from: '/docs/guides/connectors/zed', to: '/docs/build/connectors/zed' },
          { from: '/docs/guides/connectors/zep', to: '/docs/build/connectors/zep' },
          { from: '/docs/sdks/go', to: '/docs/build/sdks/go' },
          { from: '/docs/sdks/typescript', to: '/docs/build/sdks/typescript' },
          { from: '/docs/build/guides/python-sdk', to: '/docs/build/sdks/python' },
          { from: '/docs/build/sdks/typescript-sdk', to: '/docs/build/sdks/typescript' },
          { from: '/docs/tutorials/agent-with-recall', to: '/docs/build/tutorials/agent-with-recall' },
          { from: '/docs/tutorials/authoring-lazy-discovery-instructions', to: '/docs/build/tutorials/authoring-lazy-discovery-instructions' },
          { from: '/docs/tutorials/hardening-a-stigmem-deployment', to: '/docs/build/tutorials/hardening-a-stigmem-deployment' },
          { from: '/docs/tutorials/sdk-quickstart', to: '/docs/build/tutorials/sdk-quickstart' },
          { from: '/docs/tutorials/self-host-obsidian', to: '/docs/build/tutorials/self-host-obsidian' },
          { from: '/docs/tutorials/two-org-federation', to: '/docs/build/tutorials/two-org-federation' },

          // --- operate/ (was operating/, operators/, security/, + top-level) ---
          { from: '/docs/install', to: '/docs/operate/deployment/install' },
          { from: '/docs/helm', to: '/docs/operate/deployment/helm' },
          { from: '/docs/backends', to: '/docs/operate/backends' },
          { from: '/docs/operating', to: '/docs/operate' },
          { from: '/docs/operating/choose-backend', to: '/docs/operate/backends/choose-backend' },
          { from: '/docs/operating/deploy-runbooks', to: '/docs/operate/runbooks/deploy-runbooks' },
          { from: '/docs/operating/backup-restore', to: '/docs/operate/runbooks/backup-restore' },
          { from: '/docs/operating/federation-setup', to: '/docs/operate/runbooks/federation-setup' },
          { from: '/docs/operating/key-rotation', to: '/docs/operate/runbooks/key-rotation' },
          { from: '/docs/operating/monitoring', to: '/docs/operate/observability/monitoring' },
          { from: '/docs/operating/cost-calculator', to: '/docs/operate/cost-calculator' },
          { from: '/docs/security', to: '/docs/operate/security' },
          { from: '/docs/security/audit-and-quotas', to: '/docs/operate/security/audit-and-quotas' },
          { from: '/docs/security/key-rotation', to: '/docs/operate/runbooks/key-rotation' },
          { from: '/docs/security/mtls', to: '/docs/operate/security/mtls' },
          { from: '/docs/security/pen-test', to: '/docs/operate/security/pen-test' },
          { from: '/docs/operators/container-hardening', to: '/docs/operate/security/container-hardening' },
          { from: '/docs/operators/audit-and-quotas', to: '/docs/operate/security/audit-and-quotas' },
          { from: '/docs/operators/observability', to: '/docs/operate/observability' },
          { from: '/docs/operators/eval-harness', to: '/docs/operate/observability/eval-harness' },

          // --- reference/ (was api-reference/, spec/, architecture/) ---
          { from: '/docs/api-reference', to: '/docs/reference/api' },
          { from: '/docs/spec', to: '/docs/reference/spec' },
          { from: '/docs/architecture', to: '/docs/reference/architecture' },

          // --- community/ (was contributing/, + top-level roadmap) ---
          { from: '/docs/contributing/security', to: '/docs/community/security-disclosure' },
          { from: '/docs/roadmap', to: '/docs/learn/features' },
          { from: '/docs/community/roadmap', to: '/docs/learn/features' },
          { from: '/docs/learn/concepts/state-of-stigmem', to: '/docs/learn/features' },

          // --- intermediate redirects (only for paths whose .md was removed) ---
          { from: '/docs/community/security-contributing', to: '/docs/community/security-disclosure' },
          { from: '/docs/learn/concepts/security', to: '/docs/community/security-disclosure' },
          { from: '/docs/build/guides/backup-restore', to: '/docs/operate/runbooks/backup-restore' },
          { from: '/docs/operate/security/security-key-rotation', to: '/docs/operate/runbooks/key-rotation' },
          { from: '/docs/operate/security/key-rotation', to: '/docs/operate/runbooks/key-rotation' },
          { from: '/docs/operate/security/audit-quotas-operator-quickstart', to: '/docs/operate/security/audit-and-quotas' },
        ],
      },
    ],
  ],

  themes: [
    'docusaurus-theme-openapi-docs',
    '@docusaurus/theme-live-codeblock',
    '@docusaurus/theme-mermaid',
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      image: 'img/stigmem-logo.svg',
      metadata: [
        { name: 'description', content: 'Open-source federated knowledge graph for AI agents. Immutable (entity, relation, value) facts with provenance, confidence scores, and cryptographic federation across peer nodes.' },
        { property: 'og:type', content: 'website' },
        { name: 'twitter:card', content: 'summary_large_image' },
        { name: 'twitter:site', content: '@stigmem' },
      ],
      navbar: {
        title: 'Stigmem',
        logo: { alt: 'Stigmem by Eidetic Labs', src: 'img/logo.svg' },
        items: [
          { type: 'docsVersionDropdown', position: 'left' },
          {
            type: 'docSidebar',
            sidebarId: 'learnSidebar',
            label: 'Learn',
            position: 'left',
          },
          {
            type: 'docSidebar',
            sidebarId: 'buildSidebar',
            label: 'Build',
            position: 'left',
          },
          {
            type: 'docSidebar',
            sidebarId: 'operateSidebar',
            label: 'Operate',
            position: 'left',
          },
          {
            type: 'docSidebar',
            sidebarId: 'referenceSidebar',
            label: 'Reference',
            position: 'left',
          },
          { to: '/blog', label: 'Blog', position: 'left' },
          {
            type: 'docSidebar',
            sidebarId: 'communitySidebar',
            label: 'Community',
            position: 'left',
          },
          // Custom GitHub Star/Fork pills — counts fetched live from the GitHub API
          // by the React component (shields.io's stars endpoint was returning
          // "invalid" for this repo). Cached in localStorage for 1h.
          { type: 'custom-githubButton', position: 'right', variant: 'star' },
          { type: 'custom-githubButton', position: 'right', variant: 'fork' },
        ],
      },
      footer: {
        // No `style` override — let the footer follow the page background
        // (light surface in light mode, logo-canvas dark in dark mode).
        links: [
          {
            title: 'Docs',
            items: [
              { label: 'Learn', to: '/docs/learn' },
              { label: 'Build', to: '/docs/build/guides' },
              { label: 'Operate', to: '/docs/operate' },
              { label: 'Reference', to: '/docs/reference' },
              { label: 'Features', to: '/docs/learn/features' },
            ],
          },
          {
            title: 'Community',
            items: [
              { label: 'Contributing', to: '/docs/community/security-disclosure' },
              { label: 'Project Resources', to: '/docs/community/project-resources' },
              { label: 'Blog', to: '/blog' },
            ],
          },
          {
            title: 'Project',
            items: [
              { label: 'GitHub', href: 'https://github.com/Eidetic-Labs/stigmem' },
              { label: 'License (Apache 2.0)', href: 'https://github.com/Eidetic-Labs/stigmem/blob/main/LICENSE' },
              { label: 'Security policy', href: 'https://github.com/Eidetic-Labs/stigmem/blob/main/SECURITY.md' },
            ],
          },
        ],
        copyright: `© ${new Date().getFullYear()} Eidetic Labs · Apache 2.0`,
      },
      prism: {
        theme: prismThemes.github,
        darkTheme: prismThemes.dracula,
        additionalLanguages: ['bash', 'python', 'json'],
      },
      mermaid: {
        theme: { light: 'neutral', dark: 'dark' },
        options: {
          flowchart: {
            padding: 16,
          },
        },
      },
      liveCodeBlock: {
        playgroundPosition: 'bottom',
      },
    }),
};

module.exports = config;
