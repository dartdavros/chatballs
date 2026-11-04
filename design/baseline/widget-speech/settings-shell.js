(function () {
  const { h, U, t, text, icon, card } = window.SpeechParts;
  function Sidebar({ agent }) {
    const user = { role: 'OWNER', fullName: t('owner'), email: '', organizationName: t('org'),
      organizationPublicId: 'design', memberships: [{ role: 'OWNER', organizationPublicId: 'design', organizationName: t('org') }] };
    return h('aside', { className: 'hub-sidebar' }, h('div', { className: 'hub-sidebar-body' },
      h(U.OrganizationSwitcher, { user, setRoute: () => {}, onSwitchOrganization: () => {} }),
      h(U.SidebarNavigation, { user, route: agent ? 'agents' : 'settings', setRoute: () => {}, waitingCount: 0,
        chatScope: 'all', setChatScope: () => {}, chatCounters: null }),
      h('div', { className: 'profile-link' }, h(U.Avatar, { user }), text('strong', 'owner'))));
  }
  function Navigation({ site }) {
    const user = { role: 'OWNER' };
    return h('nav', { className: 'settings-subnav', 'aria-label': t('settings') },
      h('div', { className: 'settings-subnav-head' }, text('h2', 'settings')),
      h('div', { className: 'settings-subnav-list' }, ...U.visibleSettingsSections(user).map(item => h('button', {
        key: item.key, type: 'button', className: `settings-subnav-item ${item.key === 'integrations' ? 'is-active' : ''}`,
      }, icon(item.icon, 16), h('span', null, window.SpeechProduct.translateExisting(item.label, window.SpeechLanguage))))));
  }
  function Web({ noAgent, children }) {
    const P = window.SpeechProduct;
    const items = [['main','settings'],['fields','code'],['prechat','form'],['appearance','paint'],['deleteConnection','trash']]
      .map(([key, icon]) => ({ key, label: t(key), icon, divider: key === 'appearance', danger: key === 'deleteConnection' }));
    return h(P.IntegrationPageLayout, { header: h(window.SpeechWebHeader, { noAgent }),
      items, activeKey: 'main', note: '', onSelect: () => {} }, h('div', { className: 'portal-settings-inner' },
        h('div', { className: 'portal-settings-card' }, children)));
  }
  function Agent({ children }) {
    return h('section', { className: 'sp-agent' }, h('header', { className: 'agents-header' },
      h(U.BackLink, { label: t('agents'), onClick: () => {} }), text('h2', 'agentName')),
      h('div', { className: 'sp-agent-grid' }, h('div', { className: 'sp-agent-main' },
        card('instructions', text('p', 'instructionsText')), card('knowledge', text('p', 'knowledgeText'))),
      h('div', { className: 'sp-agent-side' }, card('assignment', text('p', 'assignmentText')), children,
        card('connections', text('p', 'siteName')))));
  }
  function Screen({ frame, width, children }) {
    const agent = ['S08', 'S09', 'S10'].includes(frame.id);
    const site = /^S1[1-5]$/.test(frame.id);
    return h('div', { className: 'sp-settings-screen', style: { width }, 'data-screen': frame.id }, h(Sidebar, { agent }),
      agent ? h(Agent, null, children) : site ? h(Web, { noAgent: frame.id === 'S15' }, children)
        : h('div', { className: 'settings-layout sp-settings-layout' }, h(Navigation, { site }),
        h('section', { className: 'settings-content' }, h('div', { className: 'settings-content-inner' },
          h(U.BackLink, { label: t('integrations'), onClick: () => {} }),
          h('header', { className: 'settings-head' }, h('div', null, text('h2', site ? 'siteName' : 'speechkit'))),
          h('div', { className: 'sp-settings-body' }, children)))));
  }
  window.SpeechSettingsScreen = Screen;
})();
