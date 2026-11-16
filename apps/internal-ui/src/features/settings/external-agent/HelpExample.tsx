import { PreparedMessage } from '@chatballs/ui';
import { templateContent } from './help-example';
import { et } from './copy';
const ht = (key: 'greeting' | 'orderTitle' | 'greetingTitle') => et(`help.${key}`);

// Illustrative content in the existing prepared-message renderer and backend COMMON_CSS card.
const cardCss = '.card{width:100%;background:#fff;border:1px solid #eee;border-radius:4px 14px 14px 14px;padding:12px 13px;color:#262626;font-family:system-ui,sans-serif}';
export function HelpExample({ template = 'order' }: { template?: 'greeting' | 'order' }) {
  const greeting = { text: ht('greeting'), formatVersion: 1 as const,
    presentation: { formatVersion: 1 as const, css: cardCss, isolation: 'sandboxed-iframe' as const, sandbox: '' as const,
      srcDoc: `<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0}*{box-sizing:border-box}${cardCss}</style></head><body><div class="card">${ht('greeting')}</div></body></html>` } };
  return <div data-message-preview={template}><PreparedMessage content={template === 'order' ? templateContent() : greeting}
    title={ht(template === 'order' ? 'orderTitle' : 'greetingTitle')} /></div>;
}
