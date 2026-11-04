// WebIntegrationHeader composition. The embed URL is an explicit design example:
// file:// and about:blank have no deployment origin from which to build a snippet.
(function () {
  const { h, t, text, icon } = window.SpeechParts;
  window.SpeechWebHeader = function ({ noAgent }) {
    return h('header', { className: 'web-integration-head' },
      h('nav', { className: 'portal-breadcrumbs' },
        h('button', { className: 'link is-strong', type: 'button' }, t('settings')), h('span', null, '/'),
        h('button', { className: 'link is-muted', type: 'button' }, t('integrations')), h('span', null, '/'), text('b', 'siteName')),
      h('div', { className: 'web-integration-title' }, h('span', { className: 'web-integration-icon' }, icon('message')),
        text('h2', 'siteName'), text('span', 'working', { className: 'web-integration-status' }),
        text('span', noAgent ? 'web' : 'webAgent', { className: 'web-integration-agent' })),
      h('div', { className: 'web-integration-embed' }, h('span', { className: 'web-integration-embed-code' },
        text('code', 'snippet'), h(window.SpeechProduct.CopyButton, { value: t('snippet'), className: 'web-integration-copy' })),
        text('span', 'embedHelp')));
  };
})();
