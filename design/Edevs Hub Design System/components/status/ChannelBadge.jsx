import React from "react";

const CHANNELS = {
  max: { label: "MAX", color: "var(--channel-max)", bg: "var(--channel-max-bg)" },
  telegram: { label: "TG", color: "var(--channel-telegram)", bg: "var(--channel-telegram-bg)" },
  webchat: { label: "Web", color: "var(--channel-webchat)", bg: "var(--channel-webchat-bg)" },
};

/* ChannelBadge — differentiates MAX / Telegram / Web Chat without turning the
   UI into a colorful mosaic (ADR-HUB-0013: "channel-*" tokens). */
export function ChannelBadge(props) {
  const c = CHANNELS[props.channel];
  return React.createElement(
    "span",
    { title: props.title ?? c.label, style: { display: "inline-flex", alignItems: "center", gap: 4, padding: "2px 7px", borderRadius: 5, background: c.bg } },
    React.createElement("span", { style: { width: 5, height: 5, borderRadius: "50%", background: c.color } }),
    React.createElement("span", { style: { fontSize: 10.5, fontWeight: 600, color: c.color } }, c.label)
  );
}
