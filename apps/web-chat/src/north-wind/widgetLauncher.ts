const loaders = new Map<string, Promise<void>>();

type ShopSiteEvent = {widgetKey: string; name: string; eventId: string; data: Record<string, string | number>};

export async function emitShopSiteEvent(event: ShopSiteEvent) {
  await mountShopWidget(event.widgetKey);
  const host = window as Window & {Chatballs?: {emitEvent: (value: ShopSiteEvent) => boolean}};
  return host.Chatballs?.emitEvent(event) ?? false;
}

export function mountShopWidget(widgetKey: string, prepared?: { route: string; ticket: string }) {
  const pending = loaders.get(widgetKey);
  if (pending) return pending;
  const ready = new Promise<void>((resolve, reject) => {
    const loader = document.createElement("script");
    loader.src = "/chat-widget.js";
    loader.dataset.widgetKey = widgetKey;
    if (prepared) {
      loader.dataset.demoDialog = prepared.route;
      loader.dataset.demoEntry = prepared.ticket;
    }
    loader.async = true;
    loader.addEventListener("load", () => resolve(), {once: true});
    loader.addEventListener("error", () => {
      loaders.delete(widgetKey);
      loader.remove();
      reject(new Error("widget_unavailable"));
    }, {once: true});
    document.body.append(loader);
  });
  loaders.set(widgetKey, ready);
  return ready;
}

export async function openPreparedShopWidget(session: {widgetKey: string; token: string}) {
  if (!loaders.has(session.widgetKey)) {
    const key = `chatballs-chat-token:${session.widgetKey}`;
    localStorage.setItem(key, session.token);
    localStorage.removeItem(`${key}:consent-version`);
  }
  await mountShopWidget(session.widgetKey);
  openShopWidget();
}

export function openShopWidget() {
  const host = window as Window & {ChatballsChat?: {open: () => void}};
  if (!host.ChatballsChat?.open) throw new Error("widget_unavailable");
  host.ChatballsChat.open();
}
