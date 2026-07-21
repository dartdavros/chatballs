import { providerKey, providerLabel, providerMeta } from "../../shared/providers";

/**
 * Точка + короткий лейбл на токенах провайдера (ADR-HUB-0013).
 *
 * Применяется экономно — только в колонке «Подключения» списка и в секции
 * «Подключения» карточки, чтобы экраны не превращались в цветную мозаику.
 * Провайдеры различаются бейджем, а не бренд-логотипами.
 */
export function ChannelBadge({ provider }: { provider: string }) {
  const key = providerKey(provider);
  if (!key) {
    return <span className="channel-badge channel-badge--plain">{provider}</span>;
  }
  const meta = providerMeta[key];
  return (
    <span className="channel-badge" style={{ background: meta.bg, color: meta.color }} title={meta.label}>
      <i style={{ background: meta.color }} />
      {meta.short}
    </span>
  );
}

export { providerLabel };
