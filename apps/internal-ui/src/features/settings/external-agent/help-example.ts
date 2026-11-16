import { et } from './copy';
const tx = (key: 'orderLabel' | 'orderStatus' | 'deliveryLabel' | 'deliveryValue') => et(`chat.${key}`);

// Static example of the current backend order/status template, not a template compiler or API snapshot.
// CSS source: apps/backend/chatballs/ai/skill_templates/order_sources.py COMMON_CSS + STATUS_CSS.
const css = `html,body{margin:0;padding:0;width:100%;overflow-wrap:anywhere}*{box-sizing:border-box}
.card{width:100%;background:#fff;border:1px solid #eee;border-radius:4px 14px 14px 14px;padding:12px 13px;color:#262626;font-family:system-ui,sans-serif}
.order-no{display:block;font-size:11.5px;color:#8c8c8c;overflow-wrap:anywhere}
.status{display:inline-flex;align-items:center;gap:6px;margin-top:6px;padding:4px 10px;border-radius:12px;background:#e6f4f2;color:#0f766e;font-size:13px;font-weight:600;overflow-wrap:anywhere;max-width:100%}
.dot{width:7px;height:7px;flex:none;border-radius:50%;background:currentColor}
.eta{display:flex;align-items:center;gap:6px;margin-top:9px;padding-top:9px;border-top:1px solid #f0f0f0;font-size:12.5px;color:#595959}
.eta svg{flex:none}.eta b{color:#262626}`;
export function templateContent() {
  const text = `${tx('orderLabel')} 1042 · ${tx('orderStatus')} · ${tx('deliveryLabel')}: ${tx('deliveryValue')}`;
  const srcDoc = `<!doctype html><html><head><meta charset="utf-8"><meta name="referrer" content="no-referrer"><style>${css}</style></head><body><div class="card"><small class="order-no">${tx('orderLabel')} 1042</small><span class="status"><i class="dot"></i>${tx('orderStatus')}</span><div class="eta"><span>${tx('deliveryLabel')}: <b>${tx('deliveryValue')}</b></span></div></div></body></html>`;
  return { text, formatVersion: 1 as const, presentation: { formatVersion: 1 as const, css, isolation: 'sandboxed-iframe' as const, sandbox: '' as const, srcDoc } };
}
