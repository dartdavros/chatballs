import React from "react";
import { ActorBadge } from "../status/ActorBadge.jsx";
import { ChannelBadge } from "../status/ChannelBadge.jsx";

/* ConversationInbox — the realtime inbox list (ADR-HUB-0013 local component):
   one row per conversation with channel, last actor, wait state and time. */
export function ConversationInbox(props) {
  return React.createElement(
    "div",
    { style: { background: "var(--surface-card)", border: "1px solid var(--n-8)", borderRadius: "var(--radius-2xl)", overflow: "hidden" } },
    (props.items ?? []).map((it, i) =>
      React.createElement(
        "div",
        {
          key: i,
          onClick: it.onClick,
          style: {
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "12px 16px",
            borderTop: i === 0 ? "none" : "1px solid var(--n-9)",
            cursor: it.onClick ? "pointer" : "default",
            background: it.active ? "var(--primary-bg)" : "transparent",
          },
        },
        React.createElement(ActorBadge, { actor: it.lastActor, initials: it.initials, color: it.color }),
        React.createElement(
          "div",
          { style: { flex: 1, minWidth: 0 } },
          React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 8 } },
            React.createElement("span", { style: { fontSize: 13.5, fontWeight: 600, color: "var(--text-heading)" } }, it.name),
            React.createElement(ChannelBadge, { channel: it.channel })
          ),
          React.createElement("div", { style: { fontSize: 12, color: "var(--text-tertiary)", marginTop: 2, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" } }, it.preview)
        ),
        React.createElement(
          "div",
          { style: { display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4, flex: "none" } },
          React.createElement("span", { style: { fontSize: 11, color: "var(--text-disabled)" } }, it.time),
          it.waiting ? React.createElement("span", { style: { width: 7, height: 7, borderRadius: "50%", background: "var(--warning)" } }) : null
        )
      )
    )
  );
}
