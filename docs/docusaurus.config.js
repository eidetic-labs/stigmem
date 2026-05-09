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

  // 'warn' (not 'throw') is intentional during the v0.9.0a1 reset window:
  // ~70 doc pages were moved to Internal-Comms (deferred features) per the
  // docs-manifest. Pages that survive in public docs still have markdown
  // cross-links to those moved pages; cleaning them up is a follow-up pass.
  // Set back to 'throw' once the cross-link cleanup PR lands.
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
          // Single-version mode for v0.9.0a1 (canonical first build per ADR-001 +
          // ADR-019). Prior `v1.1` and `v0.2` versioned snapshots claimed releases
          // that never shipped publicly; archived to Internal-Comms. Multi-version
          // setup will be re-introduced when v0.9.0a2 ships and we have an actual
          // prior release to snapshot.
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
        // Only redirects for URLs already published in immutable artifact metadata
        // (PyPI wheel pyproject.toml `Documentation`, ClawHub SKILL.md, README links
        // that may have been crawled). Each entry maps a previously-shipped URL to
        // its current canonical location. Adding a new redirect here is a contract
        // change — leave existing entries alone.
        //
        // Earlier IA-migration redirects (v1.1 build/learn/operate/reference layout)
        // were removed as part of the v0.9.0a1 reset since the v1.1 IA never had
        // real users. See ADR-001/ADR-019.
        redirects: [
          { from: '/docs/guides/connectors/openclaw',  to: '/docs/sdks/connectors/openclaw' },
          // /docs/guides/connectors/obsidian was in adapters/obsidian/pyproject.toml
          // but stigmem-obsidian was never published; redirect dropped along with
          // the obsidian docs (deferred per docs-manifest).
          { from: '/docs/guides/federation',           to: '/docs/concepts/federation/' },
          { from: '/install',                          to: '/docs/operators/deployment/install' },
          { from: '/install/deploy-recipes',           to: '/docs/operators/runbooks/deploy-runbooks' },
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
              { label: 'Concepts', to: '/docs/concepts/' },
              { label: 'Get started', to: '/docs/get-started/' },
              { label: 'SDKs', to: '/docs/sdks/' },
              { label: 'Operators', to: '/docs/operators/' },
              { label: 'Reference', to: '/docs/reference/' },
              { label: 'Features', to: '/docs/concepts/features' },
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
