// Owner-supplied brand artwork. Theme variants preserve the original colors.
(function () {
  const { h } = window.ServiceParts;
  const assets = {
    bitrix: ['./assets/logos/bitrix-color.svg', './assets/logos/bitrix-white.svg'],
    amo: ['./assets/logos/amocrm.svg'],
    mindbox: ['./assets/logos/mindbox-black.svg', './assets/logos/mindbox-white.svg'],
  };
  window.ServiceLogo = function ServiceLogo({ service, compact = false }) {
    const [light, dark] = assets[service];
    return h('span', { className: `service-logo${compact ? ' is-compact' : ''}`, role: 'img', 'aria-label': window.jt(service) },
      h('img', { src: light, alt: '', className: dark ? 'service-logo-light' : undefined }),
      dark && h('img', { src: dark, alt: '', className: 'service-logo-dark' }));
  };
})();
