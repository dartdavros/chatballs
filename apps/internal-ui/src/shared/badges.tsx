import { Icon, MaxLogo, TelegramLogo } from "./icons";
import { providerKey } from "./providers";

/** Иконка канала без подложки (дизайн-базлайн v2, решение 4): Telegram/MAX —
 * фирменные глифы, Email/Web — линейные. */
export function ChannelGlyph({ provider, size = 13 }: { provider: string; size?: number }) {
  const key = providerKey(provider);
  if (key === "TG") return <TelegramLogo size={size} />;
  if (key === "MAX") return <MaxLogo size={size} />;
  if (key === "EMAIL") return <Icon name="mail" size={size} />;
  return <Icon name="message" size={size} />;
}
