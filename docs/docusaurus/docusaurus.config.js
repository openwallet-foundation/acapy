// @ts-check
// Note: type annotations allow type checking and IDEs autocompletion
require('dotenv').config()

const lightCodeTheme = require('prism-react-renderer/themes/github');
const darkCodeTheme = require('prism-react-renderer/themes/dracula');

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: `${process.env.PROJECT_TITLE}`,
  tagline: `Everything you need to know to get started`,
  url: `https://${process.env.ORGANIZATION_NAME}.github.io`,
  baseUrl: `/${process.env.PROJECT_NAME}`,
  onBrokenLinks: 'warn',
  onBrokenMarkdownLinks: 'warn',
  favicon: 'img/favicon.ico',

  // GitHub pages deployment config.
  // If you aren't using GitHub pages, you don't need these.
  organizationName: `${process.env.ORGANIZATION_NAME}`, // Usually your GitHub org/user name.
  projectName: `${process.env.PROJECT_NAME}`, // Usually your repo name.

  // Even if you don't use internalization, you can use this field to set useful
  // metadata like html lang. For example, if your site is Chinese, you may want
  // to replace "en" with "zh-Hans".
  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          // routeBasePath: '/', // Serve the docs at the site's root
          sidebarPath: require.resolve('./sidebars.js'),
          // Remove this to remove the "edit this page" links.
          editUrl: `https://github.com/${process.env.ORGANIZATION_NAME}/${process.env.PROJECT_NAME}/tree/${process.env.BRANCH_NAME}/docs/docusaurus`,
        },
        blog: false, // Disable the blog plugin
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      }),
    ],
  ],

  plugins: [
    [
      require.resolve("@cmfcmf/docusaurus-search-local"),
      {
        indexBlog: false
      }
    ],
    // [
    //   '@docusaurus/plugin-content-docs',
    //   {
    //     id: 'code',
    //     path: '../rtd/build/',
    //     routeBasePath: 'code',
    //   },
    // ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      colorMode: {
        defaultMode: 'light',
        disableSwitch: true,
        respectPrefersColorScheme: false,
      },
      navbar: {
        title: 'Aries Cloud Agent Python',
        logo: {
          alt: 'ACA-Py',
          src: 'img/aries-logo.png',
        },
        items: [
          {
            type: 'doc',
            docId: 'index',
            position: 'left',
            label: 'Documentation',
          },
          // {
          //   type: 'doc',
          //   docId: 'index',
          //   position: 'left',
          //   label: 'Code',
          //   docsPluginId: 'code'
          // },
          {
            position: 'left',
            label: 'Code',
            href: 'https://aries-cloud-agent-python.readthedocs.io/en/latest/'
          },
          {
            type: 'docsVersionDropdown',
            position: 'right',
            sidebarId: '1.0',
          },
          {
            label: 'GitHub',
            href: `https://github.com/${process.env.ORGANIZATION_NAME}/${process.env.PROJECT_NAME}`,
            position: 'right',
          },
        ],
      },
      footer: {
        style: 'dark',
        links: [
          {
            title: 'Docs',
            items: [
              {
                label: 'ACA-Py',
                to: '/',
              },
            ],
          },
          {
            title: 'More',
            items: [
              {
                label: 'GitHub',
                href: `https://github.com/${process.env.ORGANIZATION_NAME}/${process.env.PROJECT_NAME}`,
              },
            ],
          },
        ],
        // copyright: `Copyright © ${new Date().getFullYear()} My Project, Inc. Built with Docusaurus.`,
      },
      prism: {
        theme: lightCodeTheme,
        darkTheme: darkCodeTheme,
      },
    }),
};

module.exports = config;
