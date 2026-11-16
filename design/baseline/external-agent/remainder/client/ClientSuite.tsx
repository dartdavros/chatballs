import { useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { applyWidgetLanguage } from '../../../../../apps/web-chat/src/i18n';
import documentCss from '../../../../../apps/web-chat/src/styles.css?raw';
import { ClientDocument } from './ClientDocument';
import { clientLanguage } from './copy';
import type { ClientVariant } from './cases';

export { clientCases } from './cases';

// The real widget is an isolated iframe document. Shadow DOM preserves that CSS boundary.
export function ClientSuite({ variant, width, height }: { variant: ClientVariant; width: number; height: number }) {
  const host = useRef<HTMLDivElement>(null);
  const [shadow, setShadow] = useState<ShadowRoot | null>(null);
  const mobile = width <= 480;
  useLayoutEffect(() => {
    applyWidgetLanguage(clientLanguage());
    if (host.current) setShadow(host.current.shadowRoot ?? host.current.attachShadow({ mode: 'open' }));
  }, []);
  // Dimensions, position, radius and shadow match webchat/loader_assets/runtime.js.
  const panelWidth = mobile ? width : Math.min(440, width - 32);
  const panelHeight = mobile ? height : Math.min(720, height - 116);
  return <div className="ea-screen" data-screen={variant} style={{ width, height, position: 'relative' }}>
    <div ref={host} data-client-widget-host style={{
      position: 'absolute', right: mobile ? 0 : 24, bottom: mobile ? 0 : 92,
      width: panelWidth, height: panelHeight, borderRadius: mobile ? 0 : 24,
      overflow: 'hidden', boxShadow: mobile ? undefined : '0 12px 40px rgba(0,0,0,0.18)',
    }} />
    {shadow && createPortal(<>
      <style>{documentCss}</style>
      <ClientDocument variant={variant} mobile={mobile} />
    </>, shadow)}
  </div>;
}
