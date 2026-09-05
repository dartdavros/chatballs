import { Icon, MaxLogo, TelegramLogo } from "./icons";
import { providerKey, providerMeta } from "./providers";

/** Единый бейдж канала подключения из утверждённой design system. */
export function ChannelBadge({ provider }: { provider: string }) {
  const key = providerKey(provider);
  if (!key) return <span className="channel-badge is-plain">{provider}</span>;

  const meta = providerMeta[key];
  return (
    <span className="channel-badge" style={{ background: meta.bg, color: meta.color }} title={meta.label}>
      <i style={{ background: meta.color }} />
      {meta.short}
    </span>
  );
}

/** Иконка канала без подложки (дизайн-базлайн v2, решение 4): Telegram/MAX —
 * фирменные глифы, Email/Web — линейные. */
export function ChannelGlyph({ provider, size = 13 }: { provider: string; size?: number }) {
  const key = providerKey(provider);
  if (key === "TG") return <TelegramLogo size={size} />;
  if (key === "MAX") return <MaxLogo size={size} />;
  if (key === "EMAIL") return <Icon name="mail" size={size} />;
  return <Icon name="message" size={size} />;
}
