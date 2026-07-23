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
