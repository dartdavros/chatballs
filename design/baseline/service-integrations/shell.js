// SettingsPage composition with original product classes and presentation components.
// Only design-document state is owned here. No product data hooks are mounted.
(function () {
  const { h, text } = window.ServiceParts;
  const U = window.ServiceUI;
  const user = { role: 'OWNER', fullName: 'Елена Кузнецова', email: '', organizationName: 'Ателье Норд',
    organizationPublicId: 'design', memberships: [{ role: 'OWNER', organizationPublicId: 'design', organizationName: 'Ателье Норд' }] };
  const noAction = () => {};
  function Sidebar() {
    return h('aside', { className: 'hub-sidebar' },
      h('div', { className: 'hub-rail' },
        h('div', { className: 'hub-brand-mark' }, h(U.LogoIcon)),
        h('button', { className: 'hub-rail-button', title: 'Чат' }, h(U.Icon, { name: 'message', size: 18 })),
        h('button', { className: 'hub-rail-button', title: 'Развернуть меню' }, h(U.NavigationIcon, { name: 'expand' })),
        h('div', { className: 'hub-rail-spacer' }), h('button', { className: 'hub-rail-avatar', title: user.fullName }, 'ЕК')),
      h('div', { className: 'hub-sidebar-body' },
        h(U.OrganizationSwitcher, { user, setRoute: noAction, onSwitchOrganization: noAction }),
        h(U.SidebarNavigation, { user, route: 'settings', setRoute: noAction, waitingCount: 0, chatScope: 'all', setChatScope: noAction, chatCounters: null }),
        h('div', { className: 'profile-link' }, h('span', { className: 'profile-avatar' }, h(U.Avatar, { user })),
          h('span', null, text('strong', user.fullName), text('small', user.organizationName)),
          h('button', { className: 'row-menu-button profile-more', title: 'Меню пользователя' }, h(U.Icon, { name: 'more', size: 16 })))));
  }
  function Submenu({ section }) {
    return h('nav', { className: 'settings-subnav' },
      h('div', { className: 'settings-subnav-head' }, text('h2', 'Настройки')),
      h('div', { className: 'settings-subnav-list' }, ...U.visibleSettingsSections(user).map(item =>
          h('button', { key: item.key, className: `settings-subnav-item ${item.label === (section || 'Интеграции') ? 'is-active' : ''}`, type: 'button' },
          h(U.Icon, { name: item.icon, size: 16, strokeWidth: 1.9 }), text('span', item.label))),
        h('div', { className: 'settings-subnav-divider' }), text('div', 'Отдельные экраны', 'settings-subnav-caption'),
        h('button', { className: 'settings-subnav-link', type: 'button' }, h(U.Icon, { name: 'list', size: 16 }), text('span', 'Аудит действий'), h(U.Icon, { name: 'external', size: 13 }))));
  }
  function Modal({ modal }) {
    // DecisionDialog markup and styles, contained by the frame instead of a viewport portal.
    const [description, actions] = modal.content;
    return h('div', { className: 'si-modal-backdrop' }, h('section', {
      className: `decision-dialog ${modal.title.startsWith('Удалить') ? 'is-danger' : 'is-warning'} si-modal`,
      role: 'dialog', 'aria-label': modal.title,
    }, h('div', { className: 'ant-modal-content' },
      h('header', { className: 'decision-dialog-header' }, h('span', { className: 'decision-dialog-icon' }, h(U.Icon, { name: 'errorCircle', size: 22 })),
        h('div', null, text('h3', modal.title), description)),
      h('footer', { className: 'decision-dialog-footer' }, actions))));
  }
  function Screen({ item, width }) {
    const root = item.root || ['C01', 'C02', 'C09', 'C10', 'P05', 'P06'].includes(item.id);
    return h('article', { className: 'si-frame', id: item.id },
      h('div', { className: 'si-caption' }, text('code', item.id), text('strong', item.title), text('span', `${width} px`)),
      h('div', { className: 'si-screen', style: { width }, 'data-frame': item.id },
        h(Sidebar), h('div', { className: 'settings-layout si-workspace' }, h(Submenu, { section: item.section }),
          h('section', { className: 'settings-content' }, h('div', { className: 'settings-content-inner' },
            !root && h('div', { className: 'si-back' }, h(U.BackLink, { label: item.backLabel || 'Сервисы',
              onClick: () => item.backFrame ? window.ServiceShowFrame(item.backFrame) : window.ServiceNavigate('Сервисы') })),
            h('header', { className: 'settings-head' }, h('div', null, text('h2', item.heading), item.lead && text('p', item.lead)),
              item.service && h(window.ServiceLogo, { service: item.service }),
              item.action && window.ServiceParts.button(item.action, true, item.actionDisabled)),
            h('div', { className: 'si-page-body' }, ...item.content)))), item.modal && h(Modal, { modal: item.modal })));
  }
  window.ServiceScreen = Screen;
})();
