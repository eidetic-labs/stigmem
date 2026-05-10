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

  // 'warn' (not 'throw') is a temporary state during the v0.9.0a1 reset
  // window. Sub-phase 2.5.G moved ~30 deferred-feature pages out of canonical
  // docs/docs/ into experimental/<feature>/. Surviving public pages still
  // have markdown cross-links to those moved pages — each link breaks until
  // it's individually rewritten to either prose or a GitHub URL pointing at
  // experimental/<feature>/. That cleanup is acknowledged as a follow-up
  // commit within PR 2.5 or a follow-up PR; the warning surface is bounded
  // and visible in build output.
  //
  // Set back to 'throw' once the cross-link cleanup lands.
  onBrokenLinks: 'warn',

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
          // Single-version mode for v0.9.0a1 (canonical first build per
          // ADR-001 + ADR-019). Pre-reset versioned snapshots (v0.2, v1.1)
          // and the v2.0-draft "current" label labeled internal development
          // checkpoints, not tagged releases. Snapshots preserved at
          // docs/archive/snapshots/ (sub-phase 2.5.D); ADR-005's four-tab
          // IA migration lands in sub-phase 2.5.F.
          //
          // Multi-version configuration will be reintroduced when v0.9.0a2
          // ships and we have an actual prior release to snapshot
          // (docs-structure-review-2026-05-06 §8.1: "every release" snapshot
          // policy).
          versions: {
            current: {
              label: 'v0.9.0a1',
              badge: true,
              banner: 'unreleased',
            },
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
        // Redirects under v0.9.0a1 single-version mode (master-checklist
        // §4.3a, sub-phase 2.5.C). Pre-reset v1.1-IA redirects (~100 entries
        // routing to /docs/learn/, /docs/build/, /docs/operate/) targeted
        // an IA that no longer exists; those entries removed.
        //
        // The redirects below cover URLs in already-published artifact
        // metadata (PyPI wheel `Documentation` for stigmem-openclaw 0.9.0a1,
        // ClawHub `homepage`, README) plus the most-likely external-link
        // patterns that survived the v1.0 retraction. Adding a new redirect
        // here is a contract change; leave existing entries.
        //
        // Sub-phase 2.5.F (4-tab IA migration per ADR-005) will revisit
        // this list when the Learn / Build / Operate / Secure tab paths
        // settle.
        redirects: [
          { from: '/docs/guides/connectors/openclaw',  to: '/docs/sdks/connectors/openclaw' },
          { from: '/docs/guides/federation',           to: '/docs/concepts/federation/' },
          { from: '/docs/about/state-of-stigmem',      to: '/docs/concepts/features' },
          { from: '/docs/getting-started/installation', to: '/docs/get-started/installation' },
          { from: '/docs/getting-started/quickstart',  to: '/docs/get-started/quickstart-tutorial' },
          { from: '/install',                          to: '/docs/operators/deployment/install' },
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
          // Four-tab IA per ADR-005: Learn / Build / Operate / Secure.
          // Reference dissolves: API → Build, Specification → Secure,
          // Architecture splits Build/Operate, Glossary → footer utility.
          // Community dissolves: security-disclosure → Secure,
          // project-resources → footer.
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
            sidebarId: 'secureSidebar',
            label: 'Secure',
            position: 'left',
          },
          { to: '/blog', label: 'Blog', position: 'left' },
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
              { label: 'Learn', to: '/docs/concepts/' },
              { label: 'Build', to: '/docs/concepts/facts/asserting-facts' },
              { label: 'Operate', to: '/docs/operators/' },
              { label: 'Secure', to: '/docs/security/' },
              { label: 'Features', to: '/docs/concepts/features' },
            ],
          },
          {
            title: 'Reference',
            items: [
              { label: 'Glossary', to: '/docs/reference/glossary/' },
              { label: 'Architecture', to: '/docs/reference/architecture/' },
              { label: 'Experimental & Deferred', to: '/docs/reference/experimental-features' },
              { label: 'Project Resources', to: '/docs/community/project-resources' },
            ],
          },
          {
            title: 'Project',
            items: [
              { label: 'GitHub', href: 'https://github.com/Eidetic-Labs/stigmem' },
              { label: 'License (Apache 2.0)', href: 'https://github.com/Eidetic-Labs/stigmem/blob/main/LICENSE' },
              { label: 'Security policy', href: 'https://github.com/Eidetic-Labs/stigmem/blob/main/SECURITY.md' },
              { label: 'Blog', to: '/blog' },
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
            padding: 20,
          },
        },
      },
      liveCodeBlock: {
        playgroundPosition: 'bottom',
      },
    }),
};

module.exports = config;
