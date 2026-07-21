import { channelMeta } from "../conversations/data";
import type { ChannelKey } from "../conversations/types";

const PROVIDER_KEY: Record<string, ChannelKey> = { MAX: "MAX", TELEGRAM: "TG", WEB: "WEB" };
const SHORT_LABEL: Record<ChannelKey, string> = { MAX: "MAX", TG: "TG", WEB: "Web" };

/**
 * Точка + короткий лейбл на токенах провайдера (ADR-HUB-0013).
 *
 * Применяется экономно — только в колонке «Подключения» списка и в секции
 * «Подключения» карточки, чтобы экраны не превращались в цветную мозаику.
 * Провайдеры различаются бейджем, а не бренд-логотипами.
 */
export function ChannelBadge({ provider }: { provider: string }) {
  const key = PROVIDER_KEY[provider];
  if (!key) {
    return <span className="channel-badge channel-badge--plain">{provider}</span>;
  }
  const meta = channelMeta[key];
  return (
    <span className="channel-badge" style={{ background: meta.bg, color: meta.color }}>
      <i style={{ background: meta.color }} />
      {SHORT_LABEL[key]}
    </span>
  );
}

export function providerLabel(provider: string): string {
  const key = PROVIDER_KEY[provider];
  return key ? channelMeta[key].label : provider;
}
