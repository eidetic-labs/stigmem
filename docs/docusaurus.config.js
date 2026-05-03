// @ts-check
const { themes: prismThemes } = require('prism-react-renderer');

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Stigmem Protocol',
  tagline: 'Structured, federated knowledge graph for AI agents',
  favicon: 'img/favicon.ico',

  url: 'https://docs.stigmem.dev',
  baseUrl: '/',

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
          // Enables ApiItem rendering for interactive API panels (spec §5)
          docItemComponent: '@theme/ApiItem',
          lastVersion: 'current',
          versions: {
            current: { label: 'v0.5', badge: true },
            'v0.2': { label: 'v0.2', path: 'v0.2', badge: true },
          },
        },
        blog: false,
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
            outputDir: 'docs/api-reference/generated',
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
  ],

  themes: [
    'docusaurus-theme-openapi-docs',
    '@docusaurus/theme-live-codeblock',
    '@docusaurus/theme-mermaid',
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      image: 'img/logo.svg',
      navbar: {
        title: 'Stigmem',
        logo: { alt: 'Stigmem Logo', src: 'img/logo.svg' },
        items: [
          { type: 'docsVersionDropdown', position: 'left' },
          {
            type: 'docSidebar',
            sidebarId: 'gettingStartedSidebar',
            label: 'Getting Started',
            position: 'left',
          },
          {
            type: 'docSidebar',
            sidebarId: 'deploymentSidebar',
            label: 'Deployment',
            position: 'left',
          },
          {
            type: 'docSidebar',
            sidebarId: 'specSidebar',
            label: 'Spec',
            position: 'left',
          },
          {
            type: 'docSidebar',
            sidebarId: 'apiSidebar',
            label: 'API',
            position: 'left',
          },
          {
            type: 'docSidebar',
            sidebarId: 'guidesSidebar',
            label: 'Guides',
            position: 'left',
          },
          {
            type: 'docSidebar',
            sidebarId: 'architectureSidebar',
            label: 'Architecture',
            position: 'left',
          },
          {
            href: 'https://github.com/eidetic-labs/stigmem/blob/main/SECURITY.md',
            label: 'Security',
            position: 'right',
          },
          {
            href: 'https://github.com/stigmem/stigmem',
            label: 'GitHub',
            position: 'right',
          },
        ],
      },
      footer: {
        style: 'dark',
        links: [],
        copyright: `Copyright © ${new Date().getFullYear()} Acme. Apache 2.0 License.`,
      },
      prism: {
        theme: prismThemes.github,
        darkTheme: prismThemes.dracula,
        additionalLanguages: ['bash', 'python', 'json'],
      },
      mermaid: {
        theme: { light: 'neutral', dark: 'forest' },
      },
      liveCodeBlock: {
        playgroundPosition: 'bottom',
      },
    }),
};

module.exports = config;
