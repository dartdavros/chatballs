/**
 * @startingPoint section="Status" subtitle="MAX / Telegram / Web Chat channel chip" viewport="700x100"
 */
export interface ChannelBadgeProps {
  channel: "max" | "telegram" | "webchat";
  title?: string;
}

export function ChannelBadge(props: ChannelBadgeProps): JSX.Element;
