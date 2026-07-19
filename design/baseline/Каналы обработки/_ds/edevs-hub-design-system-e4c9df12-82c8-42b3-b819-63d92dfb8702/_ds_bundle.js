/* @ds-bundle: {"format":4,"namespace":"EdevsHubDesignSystem_e4c9df","components":[{"name":"CommerceStatusTimeline","sourcePath":"components/cards/CommerceStatusTimeline.jsx"},{"name":"DepartmentCard","sourcePath":"components/cards/DepartmentCard.jsx"},{"name":"IntegrationHealthCard","sourcePath":"components/cards/IntegrationHealthCard.jsx"},{"name":"MetricCard","sourcePath":"components/cards/MetricCard.jsx"},{"name":"ProductAIReleaseCard","sourcePath":"components/cards/ProductAIReleaseCard.jsx"},{"name":"Avatar","sourcePath":"components/core/Avatar.jsx"},{"name":"Button","sourcePath":"components/core/Button.jsx"},{"name":"Checkbox","sourcePath":"components/core/Checkbox.jsx"},{"name":"Icon","sourcePath":"components/core/Icon.jsx"},{"name":"ICON_NAMES","sourcePath":"components/core/Icon.jsx"},{"name":"IconButton","sourcePath":"components/core/IconButton.jsx"},{"name":"Input","sourcePath":"components/core/Input.jsx"},{"name":"Tag","sourcePath":"components/core/Tag.jsx"},{"name":"ConversationInbox","sourcePath":"components/inbox/ConversationInbox.jsx"},{"name":"KnowledgeDocumentEditor","sourcePath":"components/inbox/KnowledgeDocumentEditor.jsx"},{"name":"ActorBadge","sourcePath":"components/status/ActorBadge.jsx"},{"name":"AttentionStatus","sourcePath":"components/status/AttentionStatus.jsx"},{"name":"ChannelBadge","sourcePath":"components/status/ChannelBadge.jsx"}],"sourceHashes":{"components/cards/CommerceStatusTimeline.jsx":"a71f119a6bcb","components/cards/DepartmentCard.jsx":"743b4f9632ec","components/cards/IntegrationHealthCard.jsx":"4888c60e9532","components/cards/MetricCard.jsx":"4edb7590ee04","components/cards/ProductAIReleaseCard.jsx":"53de80d598b8","components/core/Avatar.jsx":"e963633b7162","components/core/Button.jsx":"52b57248ad92","components/core/Checkbox.jsx":"412f119cdbb2","components/core/Icon.jsx":"f6c5a199fcf5","components/core/IconButton.jsx":"e8c066b43714","components/core/Input.jsx":"4561efdc9997","components/core/Tag.jsx":"48a8a3543145","components/inbox/ConversationInbox.jsx":"ea2ad8f6a755","components/inbox/KnowledgeDocumentEditor.jsx":"f97e9057fb25","components/status/ActorBadge.jsx":"11e6274f6875","components/status/AttentionStatus.jsx":"a22cbb5b37d2","components/status/ChannelBadge.jsx":"e15a0c45d45f","ui_kits/checkout/CheckoutWidget.jsx":"6d563825a7e0","ui_kits/internal-hub/AuthLoginPage.jsx":"b3ee3d8ea9ab","ui_kits/internal-hub/ClientsPage.jsx":"0a9fb9f5b11d","ui_kits/internal-hub/CommandCenterPage.jsx":"870dd4cd0c22","ui_kits/internal-hub/HubShell.jsx":"ce0eb4d2dc70","ui_kits/web-chat/WebChatWidget.jsx":"e4099f49f9c0"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.EdevsHubDesignSystem_e4c9df = window.EdevsHubDesignSystem_e4c9df || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/cards/CommerceStatusTimeline.jsx
try { (() => {
const TONE = {
  done: "#3f8f3f",
  active: "var(--primary)",
  pending: "var(--n-6)"
};

/* CommerceStatusTimeline — separates "payment confirmed" from "product
   delivered" as distinct steps (SPEC-HUB-0007: payment and delivery states
   must never be conflated). */
function CommerceStatusTimeline(props) {
  return React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 11
    }
  }, (props.steps ?? []).map((s, i) => React.createElement("div", {
    key: i,
    style: {
      display: "flex",
      alignItems: "center",
      gap: 11
    }
  }, s.state === "done" ? React.createElement("div", {
    style: {
      width: 22,
      height: 22,
      borderRadius: "50%",
      background: "var(--success-bg-strong)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      flex: "none"
    }
  }, React.createElement("svg", {
    viewBox: "0 0 24 24",
    width: 13,
    height: 13,
    fill: "none",
    stroke: TONE.done,
    strokeWidth: 2.6,
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }, React.createElement("path", {
    d: "M20 6 9 17l-5-5"
  }))) : s.state === "active" ? React.createElement("div", {
    style: {
      width: 22,
      height: 22,
      borderRadius: "50%",
      border: `2px solid ${TONE.active}`,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      flex: "none",
      animation: "hub-pulse 1.6s ease-in-out infinite"
    }
  }, React.createElement("span", {
    style: {
      width: 7,
      height: 7,
      borderRadius: "50%",
      background: TONE.active
    }
  })) : React.createElement("div", {
    style: {
      width: 22,
      height: 22,
      borderRadius: "50%",
      border: `2px solid ${TONE.pending}`,
      flex: "none"
    }
  }), React.createElement("span", {
    style: {
      fontSize: 12.5,
      color: s.state === "active" ? "var(--text-body)" : "var(--text-secondary)",
      fontWeight: s.state === "active" ? 600 : 400
    }
  }, s.label))));
}
Object.assign(__ds_scope, { CommerceStatusTimeline });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/cards/CommerceStatusTimeline.jsx", error: String((e && e.message) || e) }); }

// components/cards/IntegrationHealthCard.jsx
try { (() => {
const STATUS = {
  connected: {
    dot: "#52c41a",
    label: "Подключено",
    color: "var(--success-text)"
  },
  degraded: {
    dot: "#faad14",
    label: "Деградация",
    color: "var(--warning-text)"
  },
  error: {
    dot: "#ff4d4f",
    label: "Ошибка",
    color: "var(--error-text)"
  }
};

/* IntegrationHealthCard — one row per external integration (payments, AI
   provider, channels, fulfillment) inside the Command Center right rail. */
function IntegrationHealthCard(props) {
  const s = STATUS[props.status ?? "connected"];
  return React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 11,
      padding: "10px 18px",
      borderTop: "1px solid var(--n-9)"
    }
  }, React.createElement("span", {
    style: {
      width: 8,
      height: 8,
      borderRadius: "50%",
      background: s.dot,
      flex: "none"
    }
  }), React.createElement("span", {
    style: {
      flex: 1,
      minWidth: 0
    }
  }, React.createElement("span", {
    style: {
      display: "block",
      fontSize: 13,
      fontWeight: 500,
      color: "var(--text-body)",
      lineHeight: 1.25
    }
  }, props.name), React.createElement("span", {
    style: {
      display: "block",
      fontSize: 11,
      color: "var(--text-disabled)"
    }
  }, props.group)), React.createElement("span", {
    style: {
      fontSize: 12,
      fontWeight: 500,
      color: s.color,
      flex: "none"
    }
  }, s.label));
}
Object.assign(__ds_scope, { IntegrationHealthCard });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/cards/IntegrationHealthCard.jsx", error: String((e && e.message) || e) }); }

// components/cards/MetricCard.jsx
try { (() => {
/* MetricCard — a single KPI cell: value + label only, per ADR-HUB-0013
   ("карточки метрик должны содержать только показатель, контекст, изменение и состояние"). */
function MetricCard(props) {
  return React.createElement("div", {
    style: {
      background: "var(--surface-card)",
      padding: "13px 15px"
    }
  }, React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 5,
      marginBottom: 7
    }
  }, props.dotColor ? React.createElement("span", {
    style: {
      width: 7,
      height: 7,
      borderRadius: "50%",
      background: props.dotColor
    }
  }) : null, React.createElement("span", {
    style: {
      fontSize: 12,
      color: "var(--text-tertiary)"
    }
  }, props.label)), React.createElement("div", {
    style: {
      fontSize: 23,
      fontWeight: 700,
      color: props.valueColor ?? "var(--text-body)",
      lineHeight: 1
    }
  }, props.value));
}
Object.assign(__ds_scope, { MetricCard });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/cards/MetricCard.jsx", error: String((e && e.message) || e) }); }

// components/core/Avatar.jsx
try { (() => {
function Avatar(props) {
  const size = props.size ?? 32;
  return React.createElement("div", {
    style: {
      width: size,
      height: size,
      borderRadius: "50%",
      background: props.color ?? "var(--primary)",
      color: "#fff",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontSize: Math.round(size * 0.38),
      fontWeight: 600,
      flex: "none"
    }
  }, props.initials);
}
Object.assign(__ds_scope, { Avatar });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Avatar.jsx", error: String((e && e.message) || e) }); }

// components/core/Button.jsx
try { (() => {
const SIZES = {
  sm: {
    h: 30,
    padX: 12,
    font: "13px"
  },
  md: {
    h: 36,
    padX: 14,
    font: "13px"
  },
  lg: {
    h: 44,
    padX: 22,
    font: "14.5px"
  }
};
function Button(props) {
  const variant = props.variant ?? "primary";
  const size = props.size ?? "md";
  const disabled = !!props.disabled;
  const s = SIZES[size] ?? SIZES.md;
  const [hover, setHover] = React.useState(false);
  const base = {
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 7,
    height: s.h,
    padding: `0 ${s.padX}px`,
    borderRadius: "var(--radius-lg)",
    fontSize: s.font,
    fontWeight: 600,
    fontFamily: "var(--font-sans)",
    cursor: disabled ? "not-allowed" : "pointer",
    border: "1px solid transparent",
    transition: "background var(--duration-fast), border-color var(--duration-fast), color var(--duration-fast)",
    opacity: disabled ? 0.55 : 1,
    whiteSpace: "nowrap"
  };
  const byVariant = {
    primary: {
      background: hover && !disabled ? "var(--primary-hover)" : "var(--primary)",
      color: "var(--text-inverse)",
      boxShadow: "var(--shadow-primary)"
    },
    secondary: {
      background: "var(--surface-card)",
      color: hover && !disabled ? "var(--primary)" : "var(--text-body)",
      borderColor: hover && !disabled ? "var(--primary)" : "var(--n-6)"
    },
    ghost: {
      background: hover && !disabled ? "var(--n-9)" : "transparent",
      color: "var(--text-body)"
    },
    danger: {
      background: hover && !disabled ? "#d9363e" : "var(--error)",
      color: "var(--text-inverse)"
    }
  };
  return React.createElement("button", {
    style: {
      ...base,
      ...byVariant[variant]
    },
    disabled,
    onClick: props.onClick,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    type: props.type ?? "button"
  }, props.children);
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Button.jsx", error: String((e && e.message) || e) }); }

// components/core/Checkbox.jsx
try { (() => {
function Checkbox(props) {
  const on = !!props.checked;
  return React.createElement("button", {
    type: "button",
    onClick: props.onChange,
    style: {
      display: "flex",
      alignItems: "flex-start",
      gap: 10,
      background: "none",
      border: "none",
      padding: 0,
      cursor: "pointer",
      textAlign: "left"
    }
  }, React.createElement("span", {
    style: {
      width: props.size === "sm" ? 17 : 20,
      height: props.size === "sm" ? 17 : 20,
      borderRadius: props.size === "sm" ? 5 : 6,
      flex: "none",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      border: on ? "none" : "1.5px solid var(--n-6)",
      background: on ? "var(--primary)" : "var(--surface-card)",
      marginTop: props.label ? 1 : 0
    }
  }, on ? React.createElement("svg", {
    viewBox: "0 0 24 24",
    width: props.size === "sm" ? 12 : 13,
    height: props.size === "sm" ? 12 : 13,
    fill: "none",
    stroke: "#fff",
    strokeWidth: 3,
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }, React.createElement("path", {
    d: "M20 6 9 17l-5-5"
  })) : null), props.label ? React.createElement("span", {
    style: {
      fontSize: 12,
      color: "var(--text-secondary)",
      lineHeight: 1.45
    }
  }, props.label) : null);
}
Object.assign(__ds_scope, { Checkbox });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Checkbox.jsx", error: String((e && e.message) || e) }); }

// components/core/Icon.jsx
try { (() => {
/* Stroke icon set copied verbatim (path data) from the approved HTML baseline
   (design/baseline/*.dc.html) — a Feather/Lucide-style outline set used
   throughout Hub, Web Chat and Checkout. Not a bundled icon font/sprite in the
   source repo: each screen inlines its own <svg>, so this component collects
   the recurring ones into one reusable primitive. */
const PATHS = {
  dashboard: '<rect x="3" y="3" width="7" height="9" rx="1.4"/><rect x="14" y="3" width="7" height="5" rx="1.4"/><rect x="14" y="12" width="7" height="9" rx="1.4"/><rect x="3" y="16" width="7" height="5" rx="1.4"/>',
  departments: '<path d="M3 21h18"/><path d="M5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16"/><path d="M9 8h1.5M13.5 8H15M9 12h1.5M13.5 12H15M9 16h1.5M13.5 16H15"/>',
  employees: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  products: '<path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>',
  ai: '<rect x="4" y="8" width="16" height="12" rx="2.5"/><path d="M12 8V4.5"/><circle cx="12" cy="3.5" r="1.2"/><circle cx="9" cy="13.5" r="1"/><circle cx="15" cy="13.5" r="1"/><path d="M2 13.5h2M20 13.5h2"/>',
  integrations: '<path d="M9 8V2.5M15 8V2.5M18 8v5.5a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V8Z"/><path d="M12 17.5V22"/>',
  settings: '<line x1="21" y1="6" x2="9" y2="6"/><line x1="3" y1="6" x2="5" y2="6"/><circle cx="7" cy="6" r="2"/><line x1="21" y1="12" x2="13" y2="12"/><line x1="3" y1="12" x2="9" y2="12"/><circle cx="11" cy="12" r="2"/><line x1="21" y1="18" x2="15" y2="18"/><line x1="3" y1="18" x2="11" y2="18"/><circle cx="13" cy="18" r="2"/>',
  search: '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
  chevronDown: '<polyline points="6 9 12 15 18 9"/>',
  chevronRight: '<polyline points="9 18 15 12 9 6"/>',
  moreVertical: '<circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  checkCircle: '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="M22 4 12 14.01l-3-3"/>',
  alertTriangle: '<path d="m21.7 18-8-14a2 2 0 0 0-3.5 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
  alertCircle: '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>',
  xCircle: '<circle cx="12" cy="12" r="9"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  refresh: '<path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/><path d="M3 21v-5h5"/>',
  arrowRight: '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
  arrowLeft: '<line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>',
  mail: '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 5L2 7"/>',
  lock: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
  eye: '<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
  eyeOff: '<path d="M9.9 4.2A9.1 9.1 0 0 1 12 4c7 0 10 8 10 8a13 13 0 0 1-1.7 2.7M6.6 6.6A13 13 0 0 0 2 12s3 8 10 8a9 9 0 0 0 3.4-.6"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/><line x1="2" y1="2" x2="22" y2="22"/>',
  card: '<rect x="2" y="5" width="20" height="14" rx="2.5"/><line x1="2" y1="10" x2="22" y2="10"/>',
  sbp: '<path d="M12 2v20M12 2 5 9M12 2l7 7M12 22l-7-7M12 22l7-7"/>',
  shield: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
  columns: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>',
  bell: '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
  trash: '<path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0-1 14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L4 6"/>',
  edit: '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
  merge: '<path d="M8 6h10M8 12h10M8 18h10"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/>',
  bolt: '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
  cart: '<path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/><path d="M3 6h18"/><path d="M16 10a4 4 0 0 1-8 0"/>',
  history: '<path d="M3 12a9 9 0 1 1 9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M3 21v-5h5"/><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/>',
  team: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  package2: '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>'
};
function Icon(props) {
  const name = props.name;
  const size = props.size ?? 17;
  const color = props.color ?? "currentColor";
  const strokeWidth = props.strokeWidth ?? 1.8;
  const d = PATHS[name];
  if (!d) return null;
  return React.createElement("svg", {
    viewBox: "0 0 24 24",
    width: size,
    height: size,
    fill: "none",
    stroke: color,
    strokeWidth: strokeWidth,
    strokeLinecap: "round",
    strokeLinejoin: "round",
    style: props.style,
    dangerouslySetInnerHTML: {
      __html: d
    }
  });
}
const ICON_NAMES = Object.keys(PATHS);
Object.assign(__ds_scope, { Icon, ICON_NAMES });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Icon.jsx", error: String((e && e.message) || e) }); }

// components/core/IconButton.jsx
try { (() => {
function IconButton(props) {
  const size = props.size ?? 36;
  const [hover, setHover] = React.useState(false);
  return React.createElement("button", {
    style: {
      position: "relative",
      width: size,
      height: size,
      borderRadius: "var(--radius-md)",
      border: props.bare ? "none" : "1px solid var(--n-8)",
      background: hover ? "var(--n-9)" : "var(--surface-card)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      cursor: "pointer",
      color: hover ? "var(--text-body)" : "var(--text-secondary)",
      flex: "none"
    },
    onClick: props.onClick,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => setHover(false),
    "aria-label": props.label,
    title: props.label
  }, props.children, props.badge ? React.createElement("span", {
    style: {
      position: "absolute",
      top: 6,
      right: 7,
      minWidth: 15,
      height: 15,
      padding: "0 4px",
      borderRadius: 8,
      background: "var(--error)",
      color: "#fff",
      fontSize: 10,
      fontWeight: 600,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      border: "1.5px solid var(--surface-card)"
    }
  }, props.badge) : null);
}
Object.assign(__ds_scope, { IconButton });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/IconButton.jsx", error: String((e && e.message) || e) }); }

// components/core/Input.jsx
try { (() => {
function Input(props) {
  const [focused, setFocused] = React.useState(false);
  const hasError = !!props.error;
  const borderColor = hasError ? "var(--error-border)" : focused ? "var(--primary)" : "var(--border-input)";
  return React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 5,
      width: props.fullWidth === false ? "auto" : "100%"
    }
  }, props.label ? React.createElement("label", {
    style: {
      fontSize: 12.5,
      fontWeight: 500,
      color: "var(--text-secondary)"
    }
  }, props.label, props.required ? React.createElement("span", {
    style: {
      color: "var(--error-text)"
    }
  }, " *") : null) : null, React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 9,
      height: "var(--h-control-lg)",
      padding: "0 13px",
      border: `1px solid ${borderColor}`,
      borderRadius: "var(--radius-lg)",
      background: props.disabled ? "var(--n-9)" : "var(--surface-card)"
    }
  }, props.icon, React.createElement("input", {
    type: props.type ?? "text",
    value: props.value,
    onChange: props.onChange,
    placeholder: props.placeholder,
    disabled: props.disabled,
    onFocus: () => setFocused(true),
    onBlur: () => setFocused(false),
    style: {
      flex: 1,
      border: "none",
      outline: "none",
      background: "transparent",
      fontSize: 14,
      color: "var(--text-body)",
      fontFamily: "var(--font-sans)",
      width: "100%"
    }
  }), props.suffix), props.hint ? React.createElement("div", {
    style: {
      fontSize: 11,
      color: hasError ? "var(--error-text)" : "var(--text-tertiary)"
    }
  }, props.hint) : null);
}
Object.assign(__ds_scope, { Input });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Input.jsx", error: String((e && e.message) || e) }); }

// components/core/Tag.jsx
try { (() => {
const TONES = {
  neutral: {
    bg: "var(--n-9)",
    color: "var(--text-secondary)",
    border: "transparent"
  },
  primary: {
    bg: "var(--primary-bg)",
    color: "#0958d9",
    border: "transparent"
  },
  success: {
    bg: "var(--success-bg)",
    color: "var(--success-text)",
    border: "var(--success-border)"
  },
  warning: {
    bg: "var(--warning-bg)",
    color: "var(--warning-text)",
    border: "var(--warning-border)"
  },
  error: {
    bg: "var(--error-bg)",
    color: "var(--error-text)",
    border: "var(--error-border)"
  },
  ai: {
    bg: "var(--ai-bg)",
    color: "var(--ai)",
    border: "transparent"
  }
};
function Tag(props) {
  const t = TONES[props.tone ?? "neutral"];
  return React.createElement("span", {
    style: {
      display: "inline-flex",
      alignItems: "center",
      gap: 6,
      padding: props.pill ? "3px 10px" : "2px 8px",
      borderRadius: props.pill ? "var(--radius-pill)" : "var(--radius-xs)",
      background: t.bg,
      border: t.border !== "transparent" ? `1px solid ${t.border}` : "none",
      fontSize: props.pill ? 12 : 11,
      fontWeight: props.pill ? 600 : 500,
      color: t.color,
      whiteSpace: "nowrap"
    }
  }, props.dot ? React.createElement("span", {
    style: {
      width: 6,
      height: 6,
      borderRadius: "50%",
      background: props.dotColor ?? t.color,
      flex: "none"
    }
  }) : null, props.children);
}
Object.assign(__ds_scope, { Tag });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Tag.jsx", error: String((e && e.message) || e) }); }

// components/cards/ProductAIReleaseCard.jsx
try { (() => {
/* ProductAIReleaseCard — a snapshot of one AI knowledge/prompt release for a
   product (e.g. Foxray, FirePage) inside the AI section. */
function ProductAIReleaseCard(props) {
  return React.createElement("div", {
    style: {
      background: "var(--surface-card)",
      border: "1px solid var(--n-8)",
      borderRadius: "var(--radius-2xl)",
      padding: "16px 18px",
      boxShadow: "var(--shadow-sm)"
    }
  }, React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      marginBottom: 10
    }
  }, React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 10
    }
  }, React.createElement("div", {
    style: {
      width: 34,
      height: 34,
      borderRadius: 9,
      background: props.iconBg ?? "var(--ai-bg)",
      color: props.iconColor ?? "var(--ai)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontSize: 14,
      fontWeight: 700,
      flex: "none"
    }
  }, props.productInitial), React.createElement("div", null, React.createElement("div", {
    style: {
      fontSize: 14.5,
      fontWeight: 700,
      color: "var(--text-heading)"
    }
  }, props.productName), React.createElement("div", {
    style: {
      fontSize: 11,
      color: "var(--text-disabled)",
      fontFamily: "var(--font-mono)"
    }
  }, props.releaseId))), React.createElement(__ds_scope.Tag, {
    pill: true,
    tone: props.live ? "success" : "neutral",
    dot: true
  }, props.live ? "Активен" : "Черновик")), React.createElement("div", {
    style: {
      display: "flex",
      gap: 1,
      background: "var(--n-8)",
      border: "1px solid var(--n-8)",
      borderRadius: "var(--radius-lg)",
      overflow: "hidden"
    }
  }, (props.stats ?? []).map((s, i) => React.createElement("div", {
    key: i,
    style: {
      flex: 1,
      background: "#fff",
      padding: "9px 11px"
    }
  }, React.createElement("div", {
    style: {
      fontSize: 11,
      color: "var(--text-tertiary)",
      marginBottom: 3
    }
  }, s.label), React.createElement("div", {
    style: {
      fontSize: 14,
      fontWeight: 600,
      color: "var(--text-body)"
    }
  }, s.value)))));
}
Object.assign(__ds_scope, { ProductAIReleaseCard });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/cards/ProductAIReleaseCard.jsx", error: String((e && e.message) || e) }); }

// components/inbox/KnowledgeDocumentEditor.jsx
try { (() => {
/* KnowledgeDocumentEditor — a minimal document editor shell for AI knowledge
   base entries (ADR-HUB-0013 local component): title, meta, and a plain
   textarea body — no rich-text chrome. */
function KnowledgeDocumentEditor(props) {
  return React.createElement("div", {
    style: {
      background: "var(--surface-card)",
      border: "1px solid var(--n-8)",
      borderRadius: "var(--radius-2xl)",
      boxShadow: "var(--shadow-sm)",
      display: "flex",
      flexDirection: "column"
    }
  }, React.createElement("div", {
    style: {
      padding: "14px 18px",
      borderBottom: "1px solid var(--n-9)",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between"
    }
  }, React.createElement("div", null, React.createElement("input", {
    value: props.title,
    onChange: props.onTitleChange,
    placeholder: "Название документа",
    style: {
      border: "none",
      outline: "none",
      fontSize: 15,
      fontWeight: 700,
      color: "var(--text-heading)",
      fontFamily: "var(--font-sans)",
      width: "100%"
    }
  }), React.createElement("div", {
    style: {
      fontSize: 11,
      color: "var(--text-disabled)",
      marginTop: 3,
      fontFamily: "var(--font-mono)"
    }
  }, props.docId)), React.createElement("span", {
    style: {
      fontSize: 11.5,
      color: "var(--text-tertiary)"
    }
  }, props.savedLabel ?? "Сохранено")), React.createElement("textarea", {
    value: props.body,
    onChange: props.onBodyChange,
    placeholder: "Текст базы знаний…",
    rows: props.rows ?? 10,
    style: {
      border: "none",
      outline: "none",
      resize: "vertical",
      padding: "16px 18px",
      fontSize: 13.5,
      lineHeight: 1.6,
      color: "var(--text-body)",
      fontFamily: "var(--font-sans)"
    }
  }));
}
Object.assign(__ds_scope, { KnowledgeDocumentEditor });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/inbox/KnowledgeDocumentEditor.jsx", error: String((e && e.message) || e) }); }

// components/status/ActorBadge.jsx
try { (() => {
/* ActorBadge — distinguishes an AI participant from a human operator in a
   conversation timeline (ADR-HUB-0013: "ai"/"human" semantic tokens). */
function ActorBadge(props) {
  const isAI = props.actor === "ai";
  if (isAI) {
    return React.createElement("div", {
      style: {
        width: 28,
        height: 28,
        borderRadius: "50%",
        background: "#eef0f2",
        border: "1px solid #e3e6ea",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flex: "none"
      }
    }, React.createElement("svg", {
      viewBox: "0 0 24 24",
      width: 15,
      height: 15,
      fill: "none",
      stroke: "#8c8c8c",
      strokeWidth: 1.8,
      strokeLinecap: "round",
      strokeLinejoin: "round"
    }, React.createElement("circle", {
      cx: 12,
      cy: 8,
      r: 3.2
    }), React.createElement("path", {
      d: "M5.5 20a6.5 6.5 0 0 1 13 0"
    })));
  }
  return React.createElement("div", {
    style: {
      width: 28,
      height: 28,
      borderRadius: "50%",
      background: props.color ?? "var(--primary)",
      color: "#fff",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontSize: 11,
      fontWeight: 600,
      flex: "none"
    }
  }, props.initials);
}
Object.assign(__ds_scope, { ActorBadge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/status/ActorBadge.jsx", error: String((e && e.message) || e) }); }

// components/status/AttentionStatus.jsx
try { (() => {
const TONE = {
  ok: {
    dot: "#52c41a",
    color: "var(--success-text)",
    bg: "var(--success-bg)",
    border: "var(--success-border)",
    label: "Нормально"
  },
  attention: {
    dot: "#faad14",
    color: "var(--warning-text)",
    bg: "var(--warning-bg)",
    border: "var(--warning-border)",
    label: "Требует внимания"
  },
  critical: {
    dot: "#ff4d4f",
    color: "var(--error-text)",
    bg: "var(--error-bg)",
    border: "var(--error-border)",
    label: "Критично"
  }
};

/* AttentionStatus — the company/department health chip (ADR-HUB-0013 local component).
   Always pairs a colored dot with a text label so color is never the only signal. */
function AttentionStatus(props) {
  const t = TONE[props.level ?? "ok"];
  return React.createElement("span", {
    style: {
      display: "inline-flex",
      alignItems: "center",
      gap: 7,
      padding: "3px 11px",
      borderRadius: "var(--radius-pill)",
      background: t.bg,
      border: `1px solid ${t.border}`
    }
  }, React.createElement("span", {
    style: {
      width: 7,
      height: 7,
      borderRadius: "50%",
      background: t.dot,
      flex: "none"
    }
  }), React.createElement("span", {
    style: {
      fontSize: 12.5,
      fontWeight: 600,
      color: t.color
    }
  }, props.label ?? t.label));
}
Object.assign(__ds_scope, { AttentionStatus });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/status/AttentionStatus.jsx", error: String((e && e.message) || e) }); }

// components/cards/DepartmentCard.jsx
try { (() => {
/* DepartmentCard — the Command Center's per-department summary
   (ADR-HUB-0013 local component). */
function DepartmentCard(props) {
  return React.createElement("div", {
    style: {
      background: "var(--surface-card)",
      border: "1px solid var(--n-8)",
      borderRadius: "var(--radius-2xl)",
      padding: "20px 22px",
      boxShadow: "var(--shadow-sm)"
    }
  }, React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "flex-start",
      gap: 14
    }
  }, React.createElement("div", {
    style: {
      width: 46,
      height: 46,
      borderRadius: 11,
      background: "var(--primary-bg)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      flex: "none"
    }
  }, React.createElement(__ds_scope.Icon, {
    name: props.icon ?? "departments",
    size: 23,
    color: "var(--primary)"
  })), React.createElement("div", {
    style: {
      flex: 1,
      minWidth: 0
    }
  }, React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 10
    }
  }, React.createElement("h3", {
    style: {
      margin: 0,
      fontSize: 18,
      fontWeight: 700,
      color: "var(--text-heading)"
    }
  }, props.name), React.createElement(__ds_scope.AttentionStatus, {
    level: props.level
  })), React.createElement("div", {
    style: {
      marginTop: 4,
      fontSize: 12.5,
      color: "var(--text-tertiary)"
    }
  }, props.meta)), React.createElement(__ds_scope.Button, {
    variant: "primary",
    onClick: props.onOpen
  }, props.openLabel ?? "Открыть отдел", React.createElement(__ds_scope.Icon, {
    name: "arrowRight",
    size: 16
  }))), props.summary ? React.createElement("div", {
    style: {
      margin: "16px 0 0",
      padding: "10px 14px",
      background: "var(--surface-sunken)",
      borderRadius: "var(--radius-md)",
      fontSize: 13,
      color: "var(--text-secondary)",
      lineHeight: 1.5
    }
  }, props.summary) : null, props.children);
}
Object.assign(__ds_scope, { DepartmentCard });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/cards/DepartmentCard.jsx", error: String((e && e.message) || e) }); }

// components/status/ChannelBadge.jsx
try { (() => {
const CHANNELS = {
  max: {
    label: "MAX",
    color: "var(--channel-max)",
    bg: "var(--channel-max-bg)"
  },
  telegram: {
    label: "TG",
    color: "var(--channel-telegram)",
    bg: "var(--channel-telegram-bg)"
  },
  webchat: {
    label: "Web",
    color: "var(--channel-webchat)",
    bg: "var(--channel-webchat-bg)"
  }
};

/* ChannelBadge — differentiates MAX / Telegram / Web Chat without turning the
   UI into a colorful mosaic (ADR-HUB-0013: "channel-*" tokens). */
function ChannelBadge(props) {
  const c = CHANNELS[props.channel];
  return React.createElement("span", {
    title: props.title ?? c.label,
    style: {
      display: "inline-flex",
      alignItems: "center",
      gap: 4,
      padding: "2px 7px",
      borderRadius: 5,
      background: c.bg
    }
  }, React.createElement("span", {
    style: {
      width: 5,
      height: 5,
      borderRadius: "50%",
      background: c.color
    }
  }), React.createElement("span", {
    style: {
      fontSize: 10.5,
      fontWeight: 600,
      color: c.color
    }
  }, c.label));
}
Object.assign(__ds_scope, { ChannelBadge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/status/ChannelBadge.jsx", error: String((e && e.message) || e) }); }

// components/inbox/ConversationInbox.jsx
try { (() => {
/* ConversationInbox — the realtime inbox list (ADR-HUB-0013 local component):
   one row per conversation with channel, last actor, wait state and time. */
function ConversationInbox(props) {
  return React.createElement("div", {
    style: {
      background: "var(--surface-card)",
      border: "1px solid var(--n-8)",
      borderRadius: "var(--radius-2xl)",
      overflow: "hidden"
    }
  }, (props.items ?? []).map((it, i) => React.createElement("div", {
    key: i,
    onClick: it.onClick,
    style: {
      display: "flex",
      alignItems: "center",
      gap: 12,
      padding: "12px 16px",
      borderTop: i === 0 ? "none" : "1px solid var(--n-9)",
      cursor: it.onClick ? "pointer" : "default",
      background: it.active ? "var(--primary-bg)" : "transparent"
    }
  }, React.createElement(__ds_scope.ActorBadge, {
    actor: it.lastActor,
    initials: it.initials,
    color: it.color
  }), React.createElement("div", {
    style: {
      flex: 1,
      minWidth: 0
    }
  }, React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 8
    }
  }, React.createElement("span", {
    style: {
      fontSize: 13.5,
      fontWeight: 600,
      color: "var(--text-heading)"
    }
  }, it.name), React.createElement(__ds_scope.ChannelBadge, {
    channel: it.channel
  })), React.createElement("div", {
    style: {
      fontSize: 12,
      color: "var(--text-tertiary)",
      marginTop: 2,
      whiteSpace: "nowrap",
      overflow: "hidden",
      textOverflow: "ellipsis"
    }
  }, it.preview)), React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      alignItems: "flex-end",
      gap: 4,
      flex: "none"
    }
  }, React.createElement("span", {
    style: {
      fontSize: 11,
      color: "var(--text-disabled)"
    }
  }, it.time), it.waiting ? React.createElement("span", {
    style: {
      width: 7,
      height: 7,
      borderRadius: "50%",
      background: "var(--warning)"
    }
  }) : null))));
}
Object.assign(__ds_scope, { ConversationInbox });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/inbox/ConversationInbox.jsx", error: String((e && e.message) || e) }); }

// ui_kits/checkout/CheckoutWidget.jsx
try { (() => {
const {
  CommerceStatusTimeline,
  Icon,
  Checkbox
} = window.EdevsHubDesignSystem_e4c9df;

/* Recreation of design/baseline/CheckoutPanel.dc.html — the public
   pay.hub.edevs.tech checkout flow (SPEC-HUB-0007). Mobile-first, no Hub chrome. */
function CheckoutWidget() {
  const [st, setSt] = React.useState("checkout");
  const [buyer, setBuyer] = React.useState("person");
  const [pay, setPay] = React.useState("card");
  const [a1, setA1] = React.useState(false);
  const [a2, setA2] = React.useState(false);
  const ready = a1 && a2;
  const seg = k => ({
    flex: 1,
    height: 36,
    borderRadius: 8,
    border: "none",
    fontSize: 12.5,
    fontWeight: 600,
    cursor: "pointer",
    background: buyer === k ? "#1f1f1f" : "transparent",
    color: buyer === k ? "#fff" : "#8c8c8c"
  });
  const cardBox = sel => ({
    display: "flex",
    alignItems: "center",
    gap: 12,
    width: "100%",
    padding: "11px 13px",
    borderRadius: 12,
    background: "#fff",
    cursor: "pointer",
    textAlign: "left",
    border: `1.5px solid ${sel ? "var(--primary)" : "#ececec"}`,
    boxShadow: sel ? "0 0 0 3px rgba(22,119,255,0.08)" : "none"
  });
  const dot = sel => ({
    width: 18,
    height: 18,
    borderRadius: "50%",
    flex: "none",
    border: sel ? "5px solid var(--primary)" : "2px solid #d9d9d9",
    background: "#fff"
  });
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      height: "100%",
      width: "100%",
      background: "#f4f5f7",
      fontFamily: "var(--font-sans)",
      color: "#1f1f1f",
      overflow: "hidden"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: "none",
      background: "#fff",
      borderBottom: "1px solid #ececec",
      padding: "13px 18px",
      display: "flex",
      alignItems: "center",
      gap: 10
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 30,
      height: 30,
      borderRadius: 8,
      background: "#1f1f1f",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: "#fff",
      fontSize: 14,
      fontWeight: 800,
      flex: "none"
    }
  }, "F"), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 14,
      fontWeight: 700,
      lineHeight: 1.1
    }
  }, "Foxray"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11,
      color: "#9a9a9a",
      marginTop: 1
    }
  }, "\u041E\u0444\u043E\u0440\u043C\u043B\u0435\u043D\u0438\u0435 \u043F\u043E\u043A\u0443\u043F\u043A\u0438")), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 5,
      padding: "4px 9px",
      borderRadius: 7,
      background: "#f1f6ec",
      border: "1px solid #d7ead0",
      flex: "none"
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "shield",
    size: 12,
    color: "#3f8f3f",
    strokeWidth: 2.2
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 10.5,
      fontWeight: 600,
      color: "#3f8f3f"
    }
  }, "\u0417\u0430\u0449\u0438\u0449\u0435\u043D\u043E")), /*#__PURE__*/React.createElement("select", {
    value: st,
    onChange: e => setSt(e.target.value),
    style: {
      marginLeft: 8,
      fontSize: 10.5,
      border: "1px solid #ececec",
      borderRadius: 6,
      background: "#fafafa"
    }
  }, ["checkout", "preparing", "pending", "paid", "delivering", "done", "error", "expired"].map(s => /*#__PURE__*/React.createElement("option", {
    key: s,
    value: s
  }, s)))), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      minHeight: 0,
      overflowY: "auto"
    }
  }, st === "expired" && /*#__PURE__*/React.createElement(StateScreen, {
    icon: "alertCircle",
    tone: "#8c8c8c",
    title: "\u0421\u0441\u044B\u043B\u043A\u0430 \u0431\u043E\u043B\u044C\u0448\u0435 \u043D\u0435 \u0434\u0435\u0439\u0441\u0442\u0432\u0443\u0435\u0442",
    body: "\u0421\u0435\u0441\u0441\u0438\u044F \u043E\u0444\u043E\u0440\u043C\u043B\u0435\u043D\u0438\u044F \u0438\u0441\u0442\u0435\u043A\u043B\u0430 \u0438\u043B\u0438 \u0431\u044B\u043B\u0430 \u043E\u0442\u043C\u0435\u043D\u0435\u043D\u0430. \u0412\u0435\u0440\u043D\u0438\u0442\u0435\u0441\u044C \u043D\u0430 \u0441\u0430\u0439\u0442 \u043F\u0440\u043E\u0434\u0443\u043A\u0442\u0430.",
    cta: "\u0412\u0435\u0440\u043D\u0443\u0442\u044C\u0441\u044F \u043D\u0430 foxray.pro"
  }), st === "preparing" && /*#__PURE__*/React.createElement(StateScreen, {
    spin: true,
    title: "\u0413\u043E\u0442\u043E\u0432\u0438\u043C \u043E\u043F\u043B\u0430\u0442\u0443",
    body: "\u041F\u0435\u0440\u0435\u043D\u0430\u043F\u0440\u0430\u0432\u043B\u044F\u0435\u043C \u043D\u0430 \u0437\u0430\u0449\u0438\u0449\u0451\u043D\u043D\u0443\u044E \u0441\u0442\u0440\u0430\u043D\u0438\u0446\u0443 \u0411\u0430\u043D\u043A\u0430 \u0422\u043E\u0447\u043A\u0430. \u041D\u0435 \u0437\u0430\u043A\u0440\u044B\u0432\u0430\u0439\u0442\u0435 \u043E\u043A\u043D\u043E."
  }), st === "pending" && /*#__PURE__*/React.createElement(StateScreen, {
    icon: "clock",
    tone: "var(--warning-text)",
    toneBg: "var(--warning-bg-strong)",
    title: "\u041F\u0440\u043E\u0432\u0435\u0440\u044F\u0435\u043C \u043E\u043F\u043B\u0430\u0442\u0443",
    body: "\u0411\u0430\u043D\u043A \u0435\u0449\u0451 \u043F\u043E\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0430\u0435\u0442 \u043E\u043F\u0435\u0440\u0430\u0446\u0438\u044E. \u041C\u044B \u043D\u0435 \u0441\u043E\u0437\u0434\u0430\u0451\u043C \u043D\u043E\u0432\u044B\u0439 \u0437\u0430\u043A\u0430\u0437 \u0430\u0432\u0442\u043E\u043C\u0430\u0442\u0438\u0447\u0435\u0441\u043A\u0438.",
    cta: "\u041F\u0440\u043E\u0432\u0435\u0440\u0438\u0442\u044C \u0435\u0449\u0451 \u0440\u0430\u0437"
  }), st === "error" && /*#__PURE__*/React.createElement(StateScreen, {
    icon: "xCircle",
    tone: "var(--error-text)",
    toneBg: "var(--error-bg)",
    title: "\u041F\u043B\u0430\u0442\u0451\u0436 \u043D\u0435 \u043F\u0440\u043E\u0448\u0451\u043B",
    body: "\u0411\u0430\u043D\u043A \u043E\u0442\u043A\u043B\u043E\u043D\u0438\u043B \u043E\u043F\u0435\u0440\u0430\u0446\u0438\u044E. \u0414\u0435\u043D\u044C\u0433\u0438 \u043D\u0435 \u0441\u043F\u0438\u0441\u0430\u043D\u044B. \u041C\u043E\u0436\u043D\u043E \u043F\u043E\u0432\u0442\u043E\u0440\u0438\u0442\u044C \u043E\u043F\u043B\u0430\u0442\u0443 \u0442\u043E\u0433\u043E \u0436\u0435 \u0437\u0430\u043A\u0430\u0437\u0430.",
    cta: "\u041F\u043E\u0432\u0442\u043E\u0440\u0438\u0442\u044C \u043E\u043F\u043B\u0430\u0442\u0443"
  }), st === "paid" && /*#__PURE__*/React.createElement("div", {
    style: {
      padding: "26px 16px 20px"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      textAlign: "center",
      marginBottom: 18
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 56,
      height: 56,
      borderRadius: "50%",
      background: "var(--success-bg-strong)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      marginBottom: 14
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "check",
    size: 28,
    color: "#3f8f3f",
    strokeWidth: 2.2
  })), /*#__PURE__*/React.createElement("h3", {
    style: {
      margin: 0,
      fontSize: 17,
      fontWeight: 700
    }
  }, "\u041E\u043F\u043B\u0430\u0442\u0430 \u043F\u043E\u043B\u0443\u0447\u0435\u043D\u0430"), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "7px 0 0",
      fontSize: 13,
      color: "#6b6b6b"
    }
  }, "\u0427\u0435\u043A \u043E\u0442\u043F\u0440\u0430\u0432\u043B\u0435\u043D \u043D\u0430 ", /*#__PURE__*/React.createElement("b", {
    style: {
      color: "#262626"
    }
  }, "a.kovalenko@northwind.ru"))), /*#__PURE__*/React.createElement("div", {
    style: {
      background: "#fff",
      border: "1px solid #ececec",
      borderRadius: 13,
      padding: "14px 16px",
      display: "flex",
      flexDirection: "column",
      gap: 9
    }
  }, /*#__PURE__*/React.createElement(SummaryRow, {
    k: "\u0417\u0430\u043A\u0430\u0437",
    v: "HUB-2026-004187",
    mono: true
  }), /*#__PURE__*/React.createElement(SummaryRow, {
    k: "\u041F\u0440\u043E\u0434\u0443\u043A\u0442",
    v: "Foxray Max \xB7 6 \u043C\u0435\u0441\u0442"
  }), /*#__PURE__*/React.createElement(SummaryRow, {
    k: "\u0421\u0443\u043C\u043C\u0430",
    v: "\u20BD95 040",
    bold: true
  }))), st === "delivering" && /*#__PURE__*/React.createElement("div", {
    style: {
      padding: "26px 16px 20px"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      textAlign: "center",
      marginBottom: 16
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 56,
      height: 56,
      borderRadius: "50%",
      background: "var(--primary-bg)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      marginBottom: 14
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "package2",
    size: 27,
    color: "var(--primary)"
  })), /*#__PURE__*/React.createElement("h3", {
    style: {
      margin: 0,
      fontSize: 16,
      fontWeight: 700
    }
  }, "\u0413\u043E\u0442\u043E\u0432\u0438\u043C \u0434\u043E\u0441\u0442\u0443\u043F \u043A \u043F\u0440\u043E\u0434\u0443\u043A\u0442\u0443"), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "8px 0 0",
      fontSize: 13,
      color: "#6b6b6b"
    }
  }, "\u041E\u043F\u043B\u0430\u0442\u0430 \u043F\u0440\u043E\u0448\u043B\u0430. \u041F\u043B\u0430\u0442\u0438\u0442\u044C \u043F\u043E\u0432\u0442\u043E\u0440\u043D\u043E \u043D\u0435 \u043D\u0443\u0436\u043D\u043E.")), /*#__PURE__*/React.createElement("div", {
    style: {
      background: "#fff",
      border: "1px solid #ececec",
      borderRadius: 13,
      padding: "14px 16px"
    }
  }, /*#__PURE__*/React.createElement(CommerceStatusTimeline, {
    steps: [{
      label: "Оплата подтверждена · ₽95 040",
      state: "done"
    }, {
      label: "Подготовка рабочих мест",
      state: "active"
    }]
  }))), st === "done" && /*#__PURE__*/React.createElement("div", {
    style: {
      padding: "26px 16px 20px"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      textAlign: "center",
      marginBottom: 18
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 56,
      height: 56,
      borderRadius: "50%",
      background: "var(--success-bg-strong)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      marginBottom: 14
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "checkCircle",
    size: 28,
    color: "#3f8f3f",
    strokeWidth: 2.2
  })), /*#__PURE__*/React.createElement("h3", {
    style: {
      margin: 0,
      fontSize: 17,
      fontWeight: 700
    }
  }, "\u0413\u043E\u0442\u043E\u0432\u043E \u2014 \u0434\u043E\u0441\u0442\u0443\u043F \u043E\u0442\u043A\u0440\u044B\u0442"), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "7px 0 0",
      fontSize: 13,
      color: "#6b6b6b"
    }
  }, "Foxray Max \u0430\u043A\u0442\u0438\u0432\u0438\u0440\u043E\u0432\u0430\u043D \u043D\u0430 6 \u043C\u0435\u0441\u0442.")), /*#__PURE__*/React.createElement("a", {
    href: "#",
    style: {
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      gap: 8,
      height: 46,
      borderRadius: 10,
      background: "var(--primary)",
      color: "#fff",
      fontSize: 14,
      fontWeight: 600,
      textDecoration: "none"
    }
  }, "\u041F\u0435\u0440\u0435\u0439\u0442\u0438 \u0432 Foxray", /*#__PURE__*/React.createElement(Icon, {
    name: "arrowRight",
    size: 16
  }))), st === "checkout" && /*#__PURE__*/React.createElement("div", {
    style: {
      padding: "16px 16px 24px",
      maxWidth: 520,
      margin: "0 auto"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      marginBottom: 14
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11,
      fontWeight: 600,
      letterSpacing: "0.06em",
      color: "#9a9a9a",
      textTransform: "uppercase",
      marginBottom: 6
    }
  }, "\u041E\u0444\u043E\u0440\u043C\u043B\u0435\u043D\u0438\u0435 \u043F\u043E\u0434\u043F\u0438\u0441\u043A\u0438"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 19,
      fontWeight: 800,
      letterSpacing: "-0.01em"
    }
  }, "Foxray Max"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 13,
      color: "#6b6b6b",
      marginTop: 3
    }
  }, "\u0413\u043E\u0434\u043E\u0432\u0430\u044F \u043F\u043E\u0434\u043F\u0438\u0441\u043A\u0430 \xB7 6 \u0440\u0430\u0431\u043E\u0447\u0438\u0445 \u043C\u0435\u0441\u0442")), /*#__PURE__*/React.createElement("div", {
    style: {
      background: "#fff",
      border: "1px solid #ececec",
      borderRadius: 13,
      overflow: "hidden",
      marginBottom: 14
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: "14px 16px 4px"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      justifyContent: "space-between",
      gap: 12,
      marginBottom: 10
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 13,
      fontWeight: 600
    }
  }, "Foxray Max"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11.5,
      color: "#9a9a9a",
      marginTop: 2
    }
  }, "6 \u043C\u0435\u0441\u0442 \xD7 \u20BD1 320 / \u043C\u0435\u0441 \xB7 12 \u043C\u0435\u0441")), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 13,
      fontWeight: 600,
      whiteSpace: "nowrap"
    }
  }, "\u20BD118 800")), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      justifyContent: "space-between",
      marginBottom: 10
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 12.5,
      color: "#3f8f3f"
    }
  }, "\u0421\u043A\u0438\u0434\u043A\u0430 \u0437\u0430 \u0433\u043E\u0434\u043E\u0432\u0443\u044E \u043E\u043F\u043B\u0430\u0442\u0443 \xB7 \u221220%"), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 12.5,
      fontWeight: 600,
      color: "#3f8f3f"
    }
  }, "\u2212\u20BD23 760"))), /*#__PURE__*/React.createElement("div", {
    style: {
      borderTop: "1px dashed #e8e8e8",
      padding: "12px 16px",
      display: "flex",
      justifyContent: "space-between",
      alignItems: "flex-end"
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 13,
      fontWeight: 700
    }
  }, "\u041F\u0435\u0440\u0432\u044B\u0439 \u043F\u043B\u0430\u0442\u0451\u0436"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11,
      color: "#9a9a9a",
      marginTop: 2
    }
  }, "\u0411\u0435\u0437 \u041D\u0414\u0421 \xB7 \u0432\u0430\u043B\u044E\u0442\u0430 \u20BD (RUB)")), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 22,
      fontWeight: 800
    }
  }, "\u20BD95 040"))), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12.5,
      fontWeight: 700,
      margin: "0 2px 9px"
    }
  }, "\u041F\u043E\u043A\u0443\u043F\u0430\u0442\u0435\u043B\u044C"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      gap: 6,
      background: "#fff",
      border: "1px solid #ececec",
      borderRadius: 11,
      padding: 4,
      marginBottom: 12
    }
  }, /*#__PURE__*/React.createElement("button", {
    style: seg("person"),
    onClick: () => setBuyer("person")
  }, "\u0424\u0438\u0437\u043B\u0438\u0446\u043E"), /*#__PURE__*/React.createElement("button", {
    style: seg("ip"),
    onClick: () => setBuyer("ip")
  }, "\u0418\u041F"), /*#__PURE__*/React.createElement("button", {
    style: seg("company"),
    onClick: () => setBuyer("company")
  }, "\u042E\u0440\u043B\u0438\u0446\u043E")), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12.5,
      fontWeight: 700,
      margin: "0 2px 9px"
    }
  }, "\u0421\u043F\u043E\u0441\u043E\u0431 \u043E\u043F\u043B\u0430\u0442\u044B"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 9,
      marginBottom: 14
    }
  }, /*#__PURE__*/React.createElement("button", {
    style: cardBox(pay === "card"),
    onClick: () => setPay("card")
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 38,
      height: 38,
      borderRadius: 9,
      background: "var(--primary-bg)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      flex: "none"
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "card",
    size: 19,
    color: "var(--primary)"
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      textAlign: "left"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 13.5,
      fontWeight: 600
    }
  }, "\u0411\u0430\u043D\u043A\u043E\u0432\u0441\u043A\u0430\u044F \u043A\u0430\u0440\u0442\u0430"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11.5,
      color: "#9a9a9a"
    }
  }, "\u0410\u0432\u0442\u043E\u043F\u0440\u043E\u0434\u043B\u0435\u043D\u0438\u0435 \u043F\u043E\u0434\u043F\u0438\u0441\u043A\u0438")), /*#__PURE__*/React.createElement("span", {
    style: dot(pay === "card")
  })), /*#__PURE__*/React.createElement("button", {
    style: cardBox(pay === "sbp"),
    onClick: () => setPay("sbp")
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 38,
      height: 38,
      borderRadius: 9,
      background: "var(--ai-bg)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      flex: "none"
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "sbp",
    size: 19,
    color: "var(--ai)"
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      textAlign: "left"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 13.5,
      fontWeight: 600
    }
  }, "\u0421\u0411\u041F"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11.5,
      color: "#9a9a9a"
    }
  }, "\u0421\u0438\u0441\u0442\u0435\u043C\u0430 \u0431\u044B\u0441\u0442\u0440\u044B\u0445 \u043F\u043B\u0430\u0442\u0435\u0436\u0435\u0439")), /*#__PURE__*/React.createElement("span", {
    style: dot(pay === "sbp")
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      background: "#fff",
      border: "1px solid #ececec",
      borderRadius: 13,
      padding: "14px 16px",
      display: "flex",
      flexDirection: "column",
      gap: 13,
      marginBottom: 90
    }
  }, /*#__PURE__*/React.createElement(Checkbox, {
    checked: a1,
    onChange: () => setA1(!a1),
    label: /*#__PURE__*/React.createElement(React.Fragment, null, "\u041F\u0440\u0438\u043D\u0438\u043C\u0430\u044E \u0443\u0441\u043B\u043E\u0432\u0438\u044F \u043F\u043E\u043A\u0443\u043F\u043A\u0438 \u0438 \u043E\u0444\u0435\u0440\u0442\u0443, \u0441\u043E\u0433\u043B\u0430\u0441\u0435\u043D \u0441 \u043F\u043E\u043B\u0438\u0442\u0438\u043A\u043E\u0439 \u043E\u0431\u0440\u0430\u0431\u043E\u0442\u043A\u0438 \u0434\u0430\u043D\u043D\u044B\u0445")
  }), /*#__PURE__*/React.createElement(Checkbox, {
    checked: a2,
    onChange: () => setA2(!a2),
    label: /*#__PURE__*/React.createElement(React.Fragment, null, "\u0421\u043E\u0433\u043B\u0430\u0441\u0435\u043D \u043D\u0430 \u0440\u0435\u0433\u0443\u043B\u044F\u0440\u043D\u044B\u0435 \u0441\u043F\u0438\u0441\u0430\u043D\u0438\u044F ", /*#__PURE__*/React.createElement("b", null, "\u20BD95 040 / \u0433\u043E\u0434"), " \u0441 \u0430\u0432\u0442\u043E\u043F\u0440\u043E\u0434\u043B\u0435\u043D\u0438\u0435\u043C \u0434\u043E \u043E\u0442\u043C\u0435\u043D\u044B")
  })))), st === "checkout" && /*#__PURE__*/React.createElement("div", {
    style: {
      flex: "none",
      background: "#fff",
      borderTop: "1px solid #ececec",
      padding: "11px 16px 14px",
      boxShadow: "var(--shadow-sticky)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      justifyContent: "space-between",
      marginBottom: 9
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 12.5,
      color: "#8c8c8c"
    }
  }, "\u041A \u043E\u043F\u043B\u0430\u0442\u0435 \u0441\u0435\u0433\u043E\u0434\u043D\u044F"), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 17,
      fontWeight: 800
    }
  }, "\u20BD95 040")), /*#__PURE__*/React.createElement("button", {
    disabled: !ready,
    style: {
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      gap: 8,
      width: "100%",
      height: 48,
      borderRadius: 11,
      border: "none",
      fontSize: 14.5,
      fontWeight: 700,
      cursor: ready ? "pointer" : "not-allowed",
      background: ready ? "var(--primary)" : "#e6e6e6",
      color: ready ? "#fff" : "#bfbfbf"
    }
  }, ready ? "Перейти к оплате" : "Примите условия выше", /*#__PURE__*/React.createElement(Icon, {
    name: "arrowRight",
    size: 16
  }))));
}
function StateScreen({
  icon,
  tone = "var(--primary)",
  toneBg = "#f4f5f7",
  title,
  body,
  cta,
  spin
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      height: "100%",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      textAlign: "center",
      padding: "40px 28px"
    }
  }, spin ? /*#__PURE__*/React.createElement("div", {
    style: {
      width: 38,
      height: 38,
      borderRadius: "50%",
      border: "3px solid #e6e6e6",
      borderTopColor: "var(--primary)",
      animation: "hub-spin .8s linear infinite",
      marginBottom: 20
    }
  }) : /*#__PURE__*/React.createElement("div", {
    style: {
      width: 54,
      height: 54,
      borderRadius: "50%",
      background: toneBg,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      marginBottom: 18
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: icon,
    size: 26,
    color: tone
  })), /*#__PURE__*/React.createElement("h3", {
    style: {
      margin: 0,
      fontSize: 16,
      fontWeight: 700
    }
  }, title), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "9px 0 0",
      fontSize: 13,
      color: "#6b6b6b",
      lineHeight: 1.55,
      maxWidth: 300
    }
  }, body), cta && /*#__PURE__*/React.createElement("button", {
    style: {
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center",
      gap: 8,
      height: 44,
      padding: "0 22px",
      marginTop: 22,
      borderRadius: 10,
      background: "var(--primary)",
      color: "#fff",
      fontSize: 13.5,
      fontWeight: 600,
      border: "none",
      cursor: "pointer"
    }
  }, cta));
}
function SummaryRow({
  k,
  v,
  mono,
  bold
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 12.5,
      color: "#8c8c8c"
    }
  }, k), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: bold ? 14 : 12.5,
      fontWeight: 600,
      color: "#262626",
      fontFamily: mono ? "var(--font-mono)" : "inherit"
    }
  }, v));
}
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/checkout/CheckoutWidget.jsx", error: String((e && e.message) || e) }); }

// ui_kits/internal-hub/AuthLoginPage.jsx
try { (() => {
const {
  Input,
  Button,
  Icon
} = window.EdevsHubDesignSystem_e4c9df;

/* Recreation of design/baseline/AUTH · Вход.dc.html */
function AuthLoginPage({
  onSuccess
}) {
  const [email, setEmail] = React.useState("");
  const [pwd, setPwd] = React.useState("");
  const [show, setShow] = React.useState(false);
  const [error, setError] = React.useState(false);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      minHeight: "100%",
      minWidth: 1024,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: "var(--surface-page)",
      fontFamily: "var(--font-sans)",
      padding: 24
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 400,
      maxWidth: "100%"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      marginBottom: 24
    }
  }, /*#__PURE__*/React.createElement("img", {
    src: "../../assets/logo-mark.svg",
    style: {
      width: 48,
      height: 48,
      borderRadius: 13,
      marginBottom: 14,
      boxShadow: "0 4px 12px var(--primary-shadow)"
    }
  }), /*#__PURE__*/React.createElement("h1", {
    style: {
      margin: 0,
      fontSize: 20,
      fontWeight: 700,
      letterSpacing: "-0.01em"
    }
  }, "Edevs Hub"), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "5px 0 0",
      fontSize: 13,
      color: "var(--text-tertiary)"
    }
  }, "\u0412\u0445\u043E\u0434 \u0432\u043E \u0432\u043D\u0443\u0442\u0440\u0435\u043D\u043D\u0438\u0439 \u043A\u0430\u0431\u0438\u043D\u0435\u0442")), /*#__PURE__*/React.createElement("div", {
    style: {
      background: "#fff",
      border: "1px solid var(--n-8)",
      borderRadius: 14,
      boxShadow: "var(--shadow-md)",
      padding: "26px 26px 24px"
    }
  }, error && /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      gap: 10,
      padding: "11px 13px",
      background: "var(--error-bg)",
      border: "1px solid var(--error-border)",
      borderRadius: 9,
      marginBottom: 18
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "alertCircle",
    size: 16,
    color: "var(--error-text)"
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 12.5,
      color: "var(--error-text)",
      lineHeight: 1.45
    }
  }, "\u041D\u0435\u0432\u0435\u0440\u043D\u044B\u0439 email \u0438\u043B\u0438 \u043F\u0430\u0440\u043E\u043B\u044C. \u041F\u0440\u043E\u0432\u0435\u0440\u044C\u0442\u0435 \u0434\u0430\u043D\u043D\u044B\u0435 \u0438 \u043F\u043E\u043F\u0440\u043E\u0431\u0443\u0439\u0442\u0435 \u0441\u043D\u043E\u0432\u0430.")), /*#__PURE__*/React.createElement("div", {
    style: {
      marginBottom: 16
    }
  }, /*#__PURE__*/React.createElement(Input, {
    label: "Email",
    icon: /*#__PURE__*/React.createElement(Icon, {
      name: "mail",
      size: 16,
      color: "var(--n-5)"
    }),
    value: email,
    onChange: e => setEmail(e.target.value),
    placeholder: "you@edevs.tech"
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      marginBottom: 22
    }
  }, /*#__PURE__*/React.createElement(Input, {
    label: "\u041F\u0430\u0440\u043E\u043B\u044C",
    type: show ? "text" : "password",
    icon: /*#__PURE__*/React.createElement(Icon, {
      name: "lock",
      size: 16,
      color: "var(--n-5)"
    }),
    suffix: /*#__PURE__*/React.createElement("button", {
      onClick: () => setShow(!show),
      style: {
        border: "none",
        background: "none",
        cursor: "pointer",
        color: "var(--n-5)",
        display: "flex"
      }
    }, /*#__PURE__*/React.createElement(Icon, {
      name: show ? "eye" : "eyeOff",
      size: 16
    })),
    value: pwd,
    onChange: e => setPwd(e.target.value),
    placeholder: "\u041F\u0430\u0440\u043E\u043B\u044C"
  })), /*#__PURE__*/React.createElement(Button, {
    variant: "primary",
    size: "lg",
    onClick: () => email && pwd ? onSuccess() : setError(true)
  }, "\u0412\u043E\u0439\u0442\u0438", /*#__PURE__*/React.createElement(Icon, {
    name: "arrowRight",
    size: 16
  }))), /*#__PURE__*/React.createElement("p", {
    style: {
      textAlign: "center",
      margin: "18px 0 0",
      fontSize: 12,
      color: "var(--n-5)"
    }
  }, "\u0414\u043E\u0441\u0442\u0443\u043F \u0442\u043E\u043B\u044C\u043A\u043E \u0434\u043B\u044F \u0441\u043E\u0442\u0440\u0443\u0434\u043D\u0438\u043A\u043E\u0432 Edevs \xB7 \u0437\u0430\u0449\u0438\u0449\u0451\u043D\u043D\u043E\u0435 \u0441\u043E\u0435\u0434\u0438\u043D\u0435\u043D\u0438\u0435")));
}
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/internal-hub/AuthLoginPage.jsx", error: String((e && e.message) || e) }); }

// ui_kits/internal-hub/ClientsPage.jsx
try { (() => {
const {
  Avatar,
  Tag,
  Icon
} = window.EdevsHubDesignSystem_e4c9df;
const DATA = [{
  name: "Мария Соколова",
  initials: "МС",
  color: "#eb6f4b",
  cid: "CUS-4821",
  email: "m.sokolova@workmail.ru",
  ch: ["MAX"],
  pr: ["FP"],
  last: "5 мин назад",
  open: 1,
  orders: 0,
  total: "—"
}, {
  name: "Дмитрий Орлов",
  initials: "ДО",
  color: "#3b82c4",
  cid: "CUS-4789",
  email: "d.orlov@gmail.com",
  ch: ["TG"],
  pr: ["FX"],
  last: "8 мин назад",
  open: 1,
  orders: 2,
  total: "₽4 980"
}, {
  name: "Елена Кузнецова",
  initials: "ЕК",
  color: "#9254de",
  cid: "CUS-4702",
  email: "e.kuznetsova@corp.ru",
  ch: ["MAX", "WEB"],
  pr: ["FX", "FP"],
  last: "18 мин назад",
  open: 1,
  orders: 3,
  total: "₽12 470"
}, {
  name: "Сергей Волков",
  initials: "СВ",
  color: "#13a8a8",
  cid: "CUS-4655",
  email: "s.volkov@mail.ru",
  ch: ["TG"],
  pr: ["FP"],
  last: "26 мин назад",
  open: 1,
  orders: 1,
  total: "₽2 490"
}, {
  name: "Павел Новиков",
  initials: "ПН",
  color: "#52a838",
  cid: "CUS-4410",
  email: "p.novikov@firm.io",
  ch: ["MAX"],
  pr: ["FP"],
  last: "1 ч назад",
  open: 0,
  orders: 4,
  total: "₽19 600"
}];
const CH = {
  MAX: {
    l: "MAX",
    c: "var(--channel-max)",
    bg: "var(--channel-max-bg)"
  },
  TG: {
    l: "TG",
    c: "var(--channel-telegram)",
    bg: "var(--channel-telegram-bg)"
  },
  WEB: {
    l: "Web",
    c: "var(--channel-webchat)",
    bg: "var(--channel-webchat-bg)"
  }
};
const PR = {
  FP: {
    n: "FirePage",
    tone: "primary"
  },
  FX: {
    n: "Foxray",
    tone: "ai"
  }
};
function ClientsPage() {
  const [q, setQ] = React.useState("");
  const rows = DATA.filter(d => !q || d.name.toLowerCase().includes(q.toLowerCase()));
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "flex-start",
      justifyContent: "space-between",
      marginBottom: 18
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h1", {
    style: {
      margin: 0,
      fontSize: 24,
      fontWeight: 700,
      letterSpacing: "-0.02em",
      color: "var(--text-heading)"
    }
  }, "\u041A\u043B\u0438\u0435\u043D\u0442\u044B"), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "6px 0 0",
      fontSize: 13.5,
      color: "var(--text-tertiary)"
    }
  }, "\u041A\u043E\u043D\u0442\u0430\u043A\u0442\u044B \u043E\u0442\u0434\u0435\u043B\u0430 \u043F\u0440\u043E\u0434\u0430\u0436 \xB7 \u043F\u043E\u043A\u0430\u0437\u0430\u043D\u043E ", rows.length, " \u0438\u0437 248"))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 12,
      background: "#fff",
      border: "1px solid var(--n-8)",
      borderRadius: 11,
      padding: "11px 14px",
      marginBottom: 16,
      boxShadow: "var(--shadow-xs)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 8,
      height: 34,
      padding: "0 11px",
      border: "1px solid var(--n-7)",
      borderRadius: 8,
      background: "var(--surface-sunken)",
      width: 280
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "search",
    size: 15,
    color: "var(--n-5)"
  }), /*#__PURE__*/React.createElement("input", {
    value: q,
    onChange: e => setQ(e.target.value),
    placeholder: "\u041F\u043E\u0438\u0441\u043A \u043F\u043E \u0438\u043C\u0435\u043D\u0438 \u0438\u043B\u0438 email\u2026",
    style: {
      border: "none",
      outline: "none",
      background: "transparent",
      fontSize: 13,
      width: "100%",
      fontFamily: "inherit"
    }
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      background: "#fff",
      border: "1px solid var(--n-8)",
      borderRadius: 12,
      boxShadow: "var(--shadow-sm)",
      overflow: "hidden"
    }
  }, /*#__PURE__*/React.createElement("table", {
    style: {
      width: "100%",
      borderCollapse: "collapse",
      fontSize: 13
    }
  }, /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", {
    style: {
      background: "var(--n-10)"
    }
  }, ["КЛИЕНТ", "КАНАЛЫ", "ПРОДУКТЫ", "ПОСЛ. ДИАЛОГ", "ОТКР.", "ЗАКАЗЫ", "СУММА ПОКУПОК"].map((h, i) => /*#__PURE__*/React.createElement("th", {
    key: i,
    style: {
      textAlign: i >= 4 ? "right" : "left",
      padding: "11px 12px",
      fontSize: 11,
      fontWeight: 600,
      color: "var(--text-tertiary)",
      borderBottom: "1px solid var(--n-8)"
    }
  }, h)))), /*#__PURE__*/React.createElement("tbody", null, rows.map((r, i) => /*#__PURE__*/React.createElement("tr", {
    key: i,
    style: {
      borderBottom: "1px solid var(--n-9)"
    }
  }, /*#__PURE__*/React.createElement("td", {
    style: {
      padding: "12px 16px"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 11
    }
  }, /*#__PURE__*/React.createElement(Avatar, {
    initials: r.initials,
    color: r.color,
    size: 34
  }), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("a", {
    href: "#",
    style: {
      fontWeight: 600,
      color: "var(--primary)",
      textDecoration: "none",
      fontSize: 13.5
    }
  }, r.name), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11,
      color: "var(--n-5)",
      fontFamily: "var(--font-mono)"
    }
  }, r.cid)))), /*#__PURE__*/React.createElement("td", {
    style: {
      padding: "12px"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      gap: 5
    }
  }, r.ch.map(c => /*#__PURE__*/React.createElement("span", {
    key: c,
    style: {
      display: "inline-flex",
      alignItems: "center",
      gap: 4,
      padding: "2px 7px",
      borderRadius: 5,
      background: CH[c].bg
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 5,
      height: 5,
      borderRadius: "50%",
      background: CH[c].c
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 10.5,
      fontWeight: 600,
      color: CH[c].c
    }
  }, CH[c].l))))), /*#__PURE__*/React.createElement("td", {
    style: {
      padding: "12px"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      gap: 5
    }
  }, r.pr.map(p => /*#__PURE__*/React.createElement(Tag, {
    key: p,
    tone: PR[p].tone
  }, PR[p].n)))), /*#__PURE__*/React.createElement("td", {
    style: {
      padding: "12px",
      color: "var(--text-secondary)"
    }
  }, r.last), /*#__PURE__*/React.createElement("td", {
    style: {
      padding: "12px",
      textAlign: "right",
      fontWeight: 600,
      color: r.open > 0 ? "var(--warning-text)" : "var(--n-5)"
    }
  }, r.open), /*#__PURE__*/React.createElement("td", {
    style: {
      padding: "12px",
      textAlign: "right",
      color: "var(--text-secondary)"
    }
  }, r.orders), /*#__PURE__*/React.createElement("td", {
    style: {
      padding: "12px",
      textAlign: "right",
      fontWeight: 600
    }
  }, r.total)))))));
}
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/internal-hub/ClientsPage.jsx", error: String((e && e.message) || e) }); }

// ui_kits/internal-hub/CommandCenterPage.jsx
try { (() => {
const {
  DepartmentCard,
  MetricCard,
  IntegrationHealthCard,
  AttentionStatus
} = window.EdevsHubDesignSystem_e4c9df;

/* Recreation of design/baseline/Командный центр.dc.html */
function CommandCenterPage({
  onOpenDepartment
}) {
  const [scenario, setScenario] = React.useState("NORMAL");
  const S = {
    NORMAL: {
      open: 42,
      active: 9,
      ai: 35,
      op: 7,
      wait: 0,
      level: "ok",
      summary: "AI ведёт большинство диалогов. Очередь оператора пуста."
    },
    ATTENTION: {
      open: 58,
      active: 14,
      ai: 41,
      op: 13,
      wait: 4,
      level: "attention",
      summary: "Очередь оператора растёт, есть незавершённые платежи."
    },
    CRITICAL: {
      open: 73,
      active: 22,
      ai: 29,
      op: 35,
      wait: 9,
      level: "critical",
      summary: "Сбой исполнения заказов и переполненная очередь операторов."
    }
  }[scenario];
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "flex-start",
      justifyContent: "space-between",
      marginBottom: 20
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h1", {
    style: {
      margin: 0,
      fontSize: 26,
      fontWeight: 700,
      letterSpacing: "-0.02em",
      color: "var(--text-heading)"
    }
  }, "\u041A\u043E\u043C\u0430\u043D\u0434\u043D\u044B\u0439 \u0446\u0435\u043D\u0442\u0440"), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "6px 0 0",
      fontSize: 13.5,
      color: "var(--text-tertiary)"
    }
  }, "\u0421\u043E\u0441\u0442\u043E\u044F\u043D\u0438\u0435 \u043A\u043E\u043C\u043F\u0430\u043D\u0438\u0438 \u043E\u0434\u043D\u0438\u043C \u0432\u0437\u0433\u043B\u044F\u0434\u043E\u043C \xB7 \u043E\u0431\u043D\u043E\u0432\u043B\u0435\u043D\u043E \u0442\u043E\u043B\u044C\u043A\u043E \u0447\u0442\u043E")), /*#__PURE__*/React.createElement("select", {
    value: scenario,
    onChange: e => setScenario(e.target.value),
    style: {
      height: 36,
      borderRadius: 8,
      border: "1px solid var(--n-6)",
      padding: "0 10px",
      fontSize: 13
    }
  }, /*#__PURE__*/React.createElement("option", {
    value: "NORMAL"
  }, "\u0421\u0446\u0435\u043D\u0430\u0440\u0438\u0439: \u041D\u043E\u0440\u043C\u0430\u043B\u044C\u043D\u043E"), /*#__PURE__*/React.createElement("option", {
    value: "ATTENTION"
  }, "\u0421\u0446\u0435\u043D\u0430\u0440\u0438\u0439: \u0412\u043D\u0438\u043C\u0430\u043D\u0438\u0435"), /*#__PURE__*/React.createElement("option", {
    value: "CRITICAL"
  }, "\u0421\u0446\u0435\u043D\u0430\u0440\u0438\u0439: \u041A\u0440\u0438\u0442\u0438\u0447\u043D\u043E"))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 16,
      background: "#fff",
      border: "1px solid var(--n-8)",
      borderLeft: `3px solid ${scenario === "NORMAL" ? "#52c41a" : scenario === "ATTENTION" ? "#faad14" : "#ff4d4f"}`,
      borderRadius: 10,
      padding: "16px 20px",
      marginBottom: 20,
      boxShadow: "var(--shadow-xs)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 10
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 16,
      fontWeight: 600,
      color: "var(--text-heading)"
    }
  }, "\u041A\u043E\u043C\u043F\u0430\u043D\u0438\u044F:"), /*#__PURE__*/React.createElement(AttentionStatus, {
    level: S.level
  })), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "3px 0 0",
      fontSize: 13.5,
      color: "var(--text-secondary)"
    }
  }, S.summary)), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      gap: 28
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      textAlign: "right"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      color: "var(--text-tertiary)"
    }
  }, "\u041E\u0442\u0434\u0435\u043B\u044B"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 18,
      fontWeight: 600
    }
  }, "1")), /*#__PURE__*/React.createElement("div", {
    style: {
      textAlign: "right"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      color: "var(--text-tertiary)"
    }
  }, "\u0412\u044B\u0440\u0443\u0447\u043A\u0430 \xB7 \u0441\u0435\u0433\u043E\u0434\u043D\u044F"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 18,
      fontWeight: 600,
      color: "var(--success-text)"
    }
  }, "\u20BD146 200")))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      gap: 20,
      alignItems: "flex-start"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 14,
      fontWeight: 600,
      color: "var(--text-secondary)",
      marginBottom: 12
    }
  }, "\u041E\u0442\u0434\u0435\u043B\u044B"), /*#__PURE__*/React.createElement(DepartmentCard, {
    name: "\u041F\u0440\u043E\u0434\u0430\u0436\u0438",
    meta: "\u041E\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0435\u043D\u043D\u044B\u0439: \u0410\u043D\u043D\u0430 \u041A\u043E\u0442\u043E\u0432\u0430 \xB7 4 \u0441\u043E\u0442\u0440\u0443\u0434\u043D\u0438\u043A\u0430 \xB7 1 AI-\u0430\u0433\u0435\u043D\u0442",
    level: S.level,
    summary: S.summary,
    onOpen: onOpenDepartment
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11,
      fontWeight: 600,
      letterSpacing: "0.05em",
      color: "var(--n-5)",
      margin: "16px 0 8px"
    }
  }, "\u0414\u0418\u0410\u041B\u041E\u0413\u0418 \u2014 \u0421\u0415\u0419\u0427\u0410\u0421"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "grid",
      gridTemplateColumns: "repeat(4,1fr)",
      gap: 1,
      background: "var(--n-8)",
      border: "1px solid var(--n-8)",
      borderRadius: 9,
      overflow: "hidden"
    }
  }, /*#__PURE__*/React.createElement(MetricCard, {
    label: "\u041E\u0442\u043A\u0440\u044B\u0442\u044B\u0435 \u0434\u0438\u0430\u043B\u043E\u0433\u0438",
    value: S.open
  }), /*#__PURE__*/React.createElement(MetricCard, {
    label: "\u0410\u043A\u0442\u0438\u0432\u043D\u044B \u0437\u0430 15 \u043C\u0438\u043D",
    value: S.active
  }), /*#__PURE__*/React.createElement(MetricCard, {
    label: "\u041D\u0430 AI",
    value: S.ai,
    dotColor: "var(--ai)"
  }), /*#__PURE__*/React.createElement(MetricCard, {
    label: "\u041E\u0436\u0438\u0434\u0430\u044E\u0442 \u043E\u043F\u0435\u0440\u0430\u0442\u043E\u0440\u0430",
    value: S.wait,
    valueColor: S.wait > 0 ? "var(--warning-text)" : undefined
  })))), /*#__PURE__*/React.createElement("div", {
    style: {
      width: 320,
      flex: "none",
      display: "flex",
      flexDirection: "column",
      gap: 16
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      background: "#fff",
      border: "1px solid var(--n-8)",
      borderRadius: 12,
      boxShadow: "var(--shadow-sm)",
      overflow: "hidden"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: "15px 18px 12px",
      fontSize: 14,
      fontWeight: 600
    }
  }, "\u0421\u043E\u0441\u0442\u043E\u044F\u043D\u0438\u0435 \u0438\u043D\u0442\u0435\u0433\u0440\u0430\u0446\u0438\u0439"), /*#__PURE__*/React.createElement(IntegrationHealthCard, {
    name: "OpenRouter",
    group: "AI-\u043F\u0440\u043E\u0432\u0430\u0439\u0434\u0435\u0440",
    status: "connected"
  }), /*#__PURE__*/React.createElement(IntegrationHealthCard, {
    name: "\u0422\u043E\u0447\u043A\u0430",
    group: "\u041F\u043B\u0430\u0442\u0435\u0436\u0438 \u0438 \u0444\u0438\u0441\u043A\u0430\u043B\u0438\u0437\u0430\u0446\u0438\u044F",
    status: scenario === "NORMAL" ? "connected" : "degraded"
  }), /*#__PURE__*/React.createElement(IntegrationHealthCard, {
    name: "Fulfillment \xB7 FirePage",
    group: "\u0418\u0441\u043F\u043E\u043B\u043D\u0435\u043D\u0438\u0435",
    status: scenario === "CRITICAL" ? "error" : "connected"
  })))));
}
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/internal-hub/CommandCenterPage.jsx", error: String((e && e.message) || e) }); }

// ui_kits/internal-hub/HubShell.jsx
try { (() => {
const {
  Icon,
  Avatar
} = window.EdevsHubDesignSystem_e4c9df;
const NAV = [{
  key: "command",
  label: "Командный центр",
  icon: "dashboard"
}, {
  section: "КОМПАНИЯ"
}, {
  key: "departments",
  label: "Отделы",
  icon: "departments"
}, {
  key: "employees",
  label: "Сотрудники",
  icon: "employees"
}, {
  key: "products",
  label: "Продукты",
  icon: "products"
}, {
  section: "ПЛАТФОРМА"
}, {
  key: "ai",
  label: "AI",
  icon: "ai"
}, {
  key: "integrations",
  label: "Интеграции",
  icon: "integrations"
}, {
  key: "settings",
  label: "Настройки",
  icon: "settings"
}];
function HubShell({
  page,
  onNavigate,
  crumb,
  children
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      height: "100%",
      minWidth: 1024,
      overflow: "hidden",
      background: "var(--surface-page)",
      fontFamily: "var(--font-sans)",
      color: "var(--text-body)"
    }
  }, /*#__PURE__*/React.createElement("aside", {
    style: {
      width: "var(--sidebar-width)",
      flex: "none",
      background: "#fff",
      borderRight: "1px solid var(--n-8)",
      display: "flex",
      flexDirection: "column"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      height: "var(--h-topbar)",
      flex: "none",
      display: "flex",
      alignItems: "center",
      gap: 11,
      padding: "0 20px",
      borderBottom: "1px solid var(--n-9)"
    }
  }, /*#__PURE__*/React.createElement("img", {
    src: "../../assets/logo-mark.svg",
    style: {
      width: 30,
      height: 30,
      borderRadius: 8
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      lineHeight: 1.15
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 14,
      fontWeight: 600,
      color: "var(--text-heading)",
      letterSpacing: "-0.01em"
    }
  }, "Edevs Hub"), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 11,
      color: "var(--text-tertiary)"
    }
  }, "\u0423\u0440\u043E\u0432\u0435\u043D\u044C \u043A\u043E\u043C\u043F\u0430\u043D\u0438\u0438"))), /*#__PURE__*/React.createElement("nav", {
    style: {
      flex: 1,
      overflowY: "auto",
      padding: "12px 12px 8px"
    }
  }, NAV.map((item, i) => item.section ? /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      fontSize: 11,
      fontWeight: 600,
      letterSpacing: "0.06em",
      color: "var(--n-5)",
      padding: "14px 12px 6px"
    }
  }, item.section) : /*#__PURE__*/React.createElement("a", {
    key: i,
    href: "#",
    onClick: e => {
      e.preventDefault();
      onNavigate(item.key);
    },
    style: {
      display: "flex",
      alignItems: "center",
      gap: 11,
      padding: "9px 12px",
      borderRadius: 8,
      textDecoration: "none",
      marginBottom: 2,
      position: "relative",
      fontSize: 13.5,
      fontWeight: page === item.key ? 600 : 500,
      background: page === item.key ? "var(--primary-bg)" : "transparent",
      color: page === item.key ? "#0958d9" : "var(--text-secondary)"
    }
  }, page === item.key && /*#__PURE__*/React.createElement("span", {
    style: {
      position: "absolute",
      left: 0,
      top: 8,
      bottom: 8,
      width: 3,
      borderRadius: "0 3px 3px 0",
      background: "var(--primary)"
    }
  }), /*#__PURE__*/React.createElement(Icon, {
    name: item.icon,
    size: 17
  }), item.label))), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: "none",
      borderTop: "1px solid var(--n-9)",
      padding: "10px 12px"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 11,
      padding: "8px 10px",
      borderRadius: 8
    }
  }, /*#__PURE__*/React.createElement(Avatar, {
    initials: "\u0418\u041F"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      lineHeight: 1.2
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 13,
      fontWeight: 600,
      color: "var(--text-body)"
    }
  }, "\u0418\u0432\u0430\u043D \u041F\u0435\u0442\u0440\u043E\u0432"), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 11,
      color: "var(--text-tertiary)"
    }
  }, "OWNER"))))), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      minWidth: 0,
      display: "flex",
      flexDirection: "column"
    }
  }, /*#__PURE__*/React.createElement("header", {
    style: {
      height: "var(--h-topbar)",
      flex: "none",
      background: "#fff",
      borderBottom: "1px solid var(--n-8)",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "0 24px"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 8,
      fontSize: 13,
      color: "var(--text-tertiary)"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontWeight: 500,
      color: "var(--text-secondary)"
    }
  }, "Edevs"), /*#__PURE__*/React.createElement("span", {
    style: {
      color: "var(--n-6)"
    }
  }, "/"), /*#__PURE__*/React.createElement("span", {
    style: {
      fontWeight: 600,
      color: "var(--text-body)"
    }
  }, crumb)), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 14
    }
  }, /*#__PURE__*/React.createElement("button", {
    style: {
      position: "relative",
      width: 36,
      height: 36,
      borderRadius: 8,
      border: "1px solid var(--n-8)",
      background: "#fff",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      cursor: "pointer",
      color: "var(--text-secondary)"
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "bell",
    size: 18
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      position: "absolute",
      top: 6,
      right: 7,
      width: 8,
      height: 8,
      borderRadius: "50%",
      background: "var(--error)",
      border: "1.5px solid #fff"
    }
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      width: 1,
      height: 24,
      background: "var(--n-8)"
    }
  }), /*#__PURE__*/React.createElement(Avatar, {
    initials: "\u0418\u041F",
    size: 28
  }))), /*#__PURE__*/React.createElement("main", {
    style: {
      flex: 1,
      overflowY: "auto",
      padding: "24px 28px 40px"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: "var(--content-max)",
      margin: "0 auto"
    }
  }, children))));
}
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/internal-hub/HubShell.jsx", error: String((e && e.message) || e) }); }

// ui_kits/web-chat/WebChatWidget.jsx
try { (() => {
const {
  ActorBadge,
  Icon
} = window.EdevsHubDesignSystem_e4c9df;

/* Recreation of design/baseline/ChatPanel.dc.html — Foxray's embedded web-chat
   widget. States: welcome (consent) / ai / operator handoff / checkout card / unavailable. */
function WebChatWidget() {
  const [state, setState] = React.useState("ai");
  const isWelcome = state === "welcome";
  const isAI = state === "ai";
  const isOperator = state === "operator";
  const isCheckout = state === "checkout";
  const isUnavailable = state === "unavailable";
  const isConversation = isAI || isOperator || isCheckout;
  const status = isOperator || isCheckout ? {
    label: "Отвечает специалист",
    dot: "#52c41a"
  } : isUnavailable ? {
    label: "Временно недоступен",
    dot: "#faad14"
  } : isWelcome ? {
    label: "Обычно отвечаем за пару минут",
    dot: "#52c41a"
  } : {
    label: "Оператор · на связи",
    dot: "#52c41a"
  };
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      height: "100%",
      width: "100%",
      background: "#fff",
      fontFamily: "var(--font-sans)",
      color: "#1f1f1f",
      overflow: "hidden"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: "none",
      background: "var(--primary)",
      padding: "14px 16px",
      display: "flex",
      alignItems: "center",
      gap: 11
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 36,
      height: 36,
      borderRadius: 10,
      background: "rgba(255,255,255,0.18)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      flex: "none",
      fontSize: 15,
      fontWeight: 700,
      color: "#fff"
    }
  }, "F"), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 14.5,
      fontWeight: 600,
      color: "#fff",
      lineHeight: 1.2
    }
  }, "Foxray"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: 6,
      marginTop: 2
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 7,
      height: 7,
      borderRadius: "50%",
      background: status.dot,
      flex: "none"
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 11.5,
      color: "rgba(255,255,255,0.92)"
    }
  }, status.label))), /*#__PURE__*/React.createElement("select", {
    value: state,
    onChange: e => setState(e.target.value),
    style: {
      background: "rgba(255,255,255,0.14)",
      color: "#fff",
      border: "none",
      borderRadius: 8,
      fontSize: 11,
      padding: "5px 6px"
    }
  }, /*#__PURE__*/React.createElement("option", {
    value: "welcome"
  }, "welcome"), /*#__PURE__*/React.createElement("option", {
    value: "ai"
  }, "ai"), /*#__PURE__*/React.createElement("option", {
    value: "operator"
  }, "operator"), /*#__PURE__*/React.createElement("option", {
    value: "checkout"
  }, "checkout"), /*#__PURE__*/React.createElement("option", {
    value: "unavailable"
  }, "unavailable"))), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      minHeight: 0,
      overflowY: "auto",
      background: "#f7f8fa",
      padding: "16px 14px"
    }
  }, isWelcome && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      textAlign: "center",
      padding: "20px 12px 8px"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 56,
      height: 56,
      borderRadius: 16,
      background: "var(--primary-bg)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      marginBottom: 14
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 24,
      fontWeight: 700,
      color: "var(--primary)"
    }
  }, "F")), /*#__PURE__*/React.createElement("h3", {
    style: {
      margin: 0,
      fontSize: 17,
      fontWeight: 700
    }
  }, "\u0427\u0430\u0442 Foxray"), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "8px 0 0",
      fontSize: 13,
      color: "#595959",
      lineHeight: 1.5,
      maxWidth: 280
    }
  }, "\u0417\u0434\u0440\u0430\u0432\u0441\u0442\u0432\u0443\u0439\u0442\u0435! \u041F\u043E\u043C\u043E\u0433\u0443 \u043F\u043E\u0434\u043E\u0431\u0440\u0430\u0442\u044C \u0442\u0430\u0440\u0438\u0444 \u0438 \u043E\u0442\u0432\u0435\u0442\u0438\u0442\u044C \u043D\u0430 \u0432\u043E\u043F\u0440\u043E\u0441\u044B \u043F\u043E Foxray. \u0427\u0435\u043C \u043C\u043E\u0436\u0435\u043C \u043F\u043E\u043C\u043E\u0447\u044C?")), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 18,
      background: "#fff",
      border: "1px solid #f0f0f0",
      borderRadius: 12,
      padding: 14
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      color: "#595959",
      lineHeight: 1.5
    }
  }, "\u041F\u0440\u043E\u0434\u043E\u043B\u0436\u0430\u044F, \u0432\u044B \u0441\u043E\u0433\u043B\u0430\u0448\u0430\u0435\u0442\u0435\u0441\u044C \u043D\u0430 \u043E\u0431\u0440\u0430\u0431\u043E\u0442\u043A\u0443 \u0441\u043E\u043E\u0431\u0449\u0435\u043D\u0438\u0439 \u0434\u043B\u044F \u043E\u0442\u0432\u0435\u0442\u0430 \u043D\u0430 \u043E\u0431\u0440\u0430\u0449\u0435\u043D\u0438\u0435. ", /*#__PURE__*/React.createElement("a", {
    href: "#",
    style: {
      color: "var(--primary)"
    }
  }, "\u041F\u043E\u043B\u0438\u0442\u0438\u043A\u0430 \u043E\u0431\u0440\u0430\u0431\u043E\u0442\u043A\u0438 \u0434\u0430\u043D\u043D\u044B\u0445"), " \xB7 \u0440\u0435\u0434. v3."))), isUnavailable && /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      textAlign: "center",
      padding: "26px 14px"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 52,
      height: 52,
      borderRadius: "50%",
      background: "var(--warning-bg-strong)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      marginBottom: 14
    }
  }, /*#__PURE__*/React.createElement(Icon, {
    name: "alertTriangle",
    size: 26,
    color: "var(--warning-text)"
  })), /*#__PURE__*/React.createElement("h3", {
    style: {
      margin: 0,
      fontSize: 15,
      fontWeight: 700
    }
  }, "\u0427\u0430\u0442 \u0432\u0440\u0435\u043C\u0435\u043D\u043D\u043E \u043D\u0435\u0434\u043E\u0441\u0442\u0443\u043F\u0435\u043D"), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: "8px 0 0",
      fontSize: 13,
      color: "#595959",
      lineHeight: 1.5,
      maxWidth: 280
    }
  }, "\u041C\u044B \u043D\u0435 \u043C\u043E\u0436\u0435\u043C \u043F\u0440\u0438\u043D\u044F\u0442\u044C \u0441\u043E\u043E\u0431\u0449\u0435\u043D\u0438\u0435 \u043F\u0440\u044F\u043C\u043E \u0441\u0435\u0439\u0447\u0430\u0441. \u041D\u0430\u043F\u0438\u0448\u0438\u0442\u0435 \u043D\u0430\u043C \u0432 \u0434\u0440\u0443\u0433\u043E\u043C \u043A\u0430\u043D\u0430\u043B\u0435."), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      flexDirection: "column",
      gap: 9,
      width: "100%",
      maxWidth: 280,
      marginTop: 18
    }
  }, /*#__PURE__*/React.createElement("a", {
    href: "#",
    style: {
      display: "flex",
      alignItems: "center",
      gap: 10,
      padding: "11px 13px",
      border: "1px solid #efdbff",
      background: "#fff",
      borderRadius: 10,
      textDecoration: "none"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 26,
      height: 26,
      borderRadius: 7,
      background: "#f2f0ff",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      flex: "none"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 9,
      height: 9,
      borderRadius: "50%",
      background: "#6b5be0"
    }
  })), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 13,
      fontWeight: 500,
      color: "#262626",
      flex: 1,
      textAlign: "left"
    }
  }, "\u041D\u0430\u043F\u0438\u0441\u0430\u0442\u044C \u0432 MAX")), /*#__PURE__*/React.createElement("a", {
    href: "#",
    style: {
      display: "flex",
      alignItems: "center",
      gap: 10,
      padding: "11px 13px",
      border: "1px solid #d6ebfa",
      background: "#fff",
      borderRadius: 10,
      textDecoration: "none"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 26,
      height: 26,
      borderRadius: 7,
      background: "#eaf6fd",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      flex: "none"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 9,
      height: 9,
      borderRadius: "50%",
      background: "#2f8fd0"
    }
  })), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 13,
      fontWeight: 500,
      color: "#262626",
      flex: 1,
      textAlign: "left"
    }
  }, "\u041D\u0430\u043F\u0438\u0441\u0430\u0442\u044C \u0432 Telegram")))), isConversation && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
    style: {
      textAlign: "center",
      marginBottom: 14
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      display: "inline-block",
      padding: "3px 11px",
      borderRadius: 20,
      background: "#eef0f2",
      fontSize: 11,
      color: "#8c8c8c"
    }
  }, "\u0421\u0435\u0433\u043E\u0434\u043D\u044F")), /*#__PURE__*/React.createElement(Bubble, {
    mine: true,
    text: "\u0417\u0434\u0440\u0430\u0432\u0441\u0442\u0432\u0443\u0439\u0442\u0435! \u0427\u0435\u043C Max \u043E\u0442\u043B\u0438\u0447\u0430\u0435\u0442\u0441\u044F \u043E\u0442 Pro?",
    time: "14:01 \xB7 \u0434\u043E\u0441\u0442\u0430\u0432\u043B\u0435\u043D\u043E"
  }), /*#__PURE__*/React.createElement(AgentBubble, {
    actor: "ai",
    text: "Pro \u2014 \u0434\u043B\u044F \u043E\u0434\u043D\u043E\u0433\u043E \u043F\u043E\u043B\u044C\u0437\u043E\u0432\u0430\u0442\u0435\u043B\u044F (\u20BD4 900/\u043C\u0435\u0441), Max \u2014 \u043A\u043E\u043C\u0430\u043D\u0434\u043D\u044B\u0439 \u0441 \u0440\u0430\u0441\u0448\u0438\u0440\u0435\u043D\u043D\u044B\u043C\u0438 \u043B\u0438\u043C\u0438\u0442\u0430\u043C\u0438 \u0438 \u043F\u0440\u0438\u043E\u0440\u0438\u0442\u0435\u0442\u043D\u043E\u0439 \u043F\u043E\u0434\u0434\u0435\u0440\u0436\u043A\u043E\u0439 (\u20BD9 900/\u043C\u0435\u0441).",
    meta: "\u041E\u043F\u0435\u0440\u0430\u0442\u043E\u0440 \xB7 14:01"
  }), /*#__PURE__*/React.createElement(Bubble, {
    mine: true,
    text: "\u041D\u0430\u0441 6 \u0447\u0435\u043B\u043E\u0432\u0435\u043A, \u0431\u0435\u0440\u0451\u043C Max \u043D\u0430 \u0433\u043E\u0434.",
    time: "14:02 \xB7 \u0434\u043E\u0441\u0442\u0430\u0432\u043B\u0435\u043D\u043E"
  }), isOperator && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
    style: {
      textAlign: "center",
      margin: "14px 0 12px"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      display: "inline-flex",
      alignItems: "center",
      gap: 6,
      padding: "5px 13px",
      borderRadius: 20,
      background: "var(--primary-bg)",
      border: "1px solid var(--primary-border)",
      fontSize: 11.5,
      color: "#0958d9",
      fontWeight: 500
    }
  }, "\u041F\u043E\u0434\u043A\u043B\u044E\u0447\u0438\u043B\u0441\u044F \u0441\u043F\u0435\u0446\u0438\u0430\u043B\u0438\u0441\u0442 \xB7 \u0438\u0441\u0442\u043E\u0440\u0438\u044F \u0443\u0436\u0435 \u0443 \u043D\u0435\u0433\u043E")), /*#__PURE__*/React.createElement(AgentBubble, {
    actor: "human",
    initials: "\u0410\u041A",
    text: "\u0417\u0434\u0440\u0430\u0432\u0441\u0442\u0432\u0443\u0439\u0442\u0435! \u0410\u043D\u043D\u0430, Foxray. \u041F\u043E\u043C\u043E\u0433\u0443 \u0441 \u043E\u0444\u043E\u0440\u043C\u043B\u0435\u043D\u0438\u0435\u043C Max \u043D\u0430 6 \u043C\u0435\u0441\u0442.",
    meta: "\u0410\u043D\u043D\u0430 \xB7 \u0441\u043F\u0435\u0446\u0438\u0430\u043B\u0438\u0441\u0442 \xB7 14:03"
  })), isAI && /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      gap: 8,
      marginBottom: 4
    }
  }, /*#__PURE__*/React.createElement(ActorBadge, {
    actor: "ai"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      background: "#fff",
      border: "1px solid #eee",
      borderRadius: "14px 14px 14px 4px",
      padding: "12px 14px",
      display: "flex",
      alignItems: "center",
      gap: 5
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 6,
      height: 6,
      borderRadius: "50%",
      background: "var(--ai-lighter)",
      animation: "hub-typing 1.2s infinite ease-in-out"
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      width: 6,
      height: 6,
      borderRadius: "50%",
      background: "var(--ai-lighter)",
      animation: "hub-typing 1.2s infinite ease-in-out .2s"
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      width: 6,
      height: 6,
      borderRadius: "50%",
      background: "var(--ai-lighter)",
      animation: "hub-typing 1.2s infinite ease-in-out .4s"
    }
  }))), isCheckout && /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      gap: 8,
      marginBottom: 6
    }
  }, /*#__PURE__*/React.createElement(ActorBadge, {
    actor: "human",
    initials: "\u0410\u041A",
    color: "var(--primary)"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: "84%",
      width: "100%"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      background: "#fff",
      border: "1px solid #e8e8e8",
      borderRadius: 14,
      overflow: "hidden",
      boxShadow: "var(--shadow-sm)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: "13px 15px 11px",
      borderBottom: "1px solid #f5f5f5"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11,
      fontWeight: 600,
      letterSpacing: "0.04em",
      color: "var(--ai)",
      marginBottom: 6
    }
  }, "\u041E\u0424\u041E\u0420\u041C\u041B\u0415\u041D\u0418\u0415 \u041F\u041E\u041A\u0423\u041F\u041A\u0418"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 15,
      fontWeight: 700
    }
  }, "Foxray Max \xB7 6 \u043C\u0435\u0441\u0442"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "baseline",
      gap: 7,
      marginTop: 7
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 21,
      fontWeight: 700
    }
  }, "\u20BD95 040"), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 12,
      color: "#8c8c8c"
    }
  }, "/ \u0433\u043E\u0434 \xB7 \u221220%"))), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: "11px 15px 13px"
    }
  }, /*#__PURE__*/React.createElement("a", {
    href: "#",
    style: {
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      gap: 7,
      height: 40,
      borderRadius: 9,
      background: "var(--primary)",
      color: "#fff",
      fontSize: 13.5,
      fontWeight: 600,
      textDecoration: "none"
    }
  }, "\u041F\u0435\u0440\u0435\u0439\u0442\u0438 \u043A \u043F\u043E\u043A\u0443\u043F\u043A\u0435", /*#__PURE__*/React.createElement(Icon, {
    name: "arrowRight",
    size: 15
  })))))))), isConversation && /*#__PURE__*/React.createElement("div", {
    style: {
      flex: "none",
      background: "#fff",
      borderTop: "1px solid #f0f0f0",
      padding: "10px 12px 12px"
    }
  }, isAI && /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      gap: 7,
      flexWrap: "wrap",
      marginBottom: 9
    }
  }, /*#__PURE__*/React.createElement(QuickReply, null, "\u0421\u0440\u0430\u0432\u043D\u0438\u0442\u044C \u0442\u0430\u0440\u0438\u0444\u044B"), /*#__PURE__*/React.createElement(QuickReply, null, "\u0415\u0441\u0442\u044C \u043B\u0438 \u043F\u0440\u043E\u0431\u043D\u044B\u0439 \u043F\u0435\u0440\u0438\u043E\u0434?")), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "flex-end",
      gap: 8,
      border: "1px solid #e8e8e8",
      borderRadius: 12,
      padding: "6px 6px 6px 12px"
    }
  }, /*#__PURE__*/React.createElement("textarea", {
    rows: 1,
    placeholder: "\u041D\u0430\u043F\u0438\u0448\u0438\u0442\u0435 \u0441\u043E\u043E\u0431\u0449\u0435\u043D\u0438\u0435\u2026",
    style: {
      flex: 1,
      border: "none",
      outline: "none",
      resize: "none",
      fontSize: 13.5,
      lineHeight: 1.5,
      color: "#262626",
      fontFamily: "inherit",
      padding: "6px 0"
    }
  }), /*#__PURE__*/React.createElement("button", {
    style: {
      width: 34,
      height: 34,
      borderRadius: 8,
      border: "none",
      background: "var(--primary)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      cursor: "pointer",
      flex: "none"
    }
  }, /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 24 24",
    width: 16,
    height: 16,
    fill: "none",
    stroke: "#fff",
    strokeWidth: 2,
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }, /*#__PURE__*/React.createElement("line", {
    x1: "22",
    y1: "2",
    x2: "11",
    y2: "13"
  }), /*#__PURE__*/React.createElement("polygon", {
    points: "22 2 15 22 11 13 2 9 22 2"
  }))))), isWelcome && /*#__PURE__*/React.createElement("div", {
    style: {
      flex: "none",
      background: "#fff",
      borderTop: "1px solid #f0f0f0",
      padding: "12px 14px 14px"
    }
  }, /*#__PURE__*/React.createElement("button", {
    onClick: () => setState("ai"),
    style: {
      width: "100%",
      height: 44,
      borderRadius: 10,
      border: "none",
      background: "var(--primary)",
      color: "#fff",
      fontSize: 14,
      fontWeight: 600,
      cursor: "pointer"
    }
  }, "\u041F\u0440\u0438\u043D\u044F\u0442\u044C \u0438 \u043D\u0430\u0447\u0430\u0442\u044C \u0447\u0430\u0442")), isUnavailable && /*#__PURE__*/React.createElement("div", {
    style: {
      flex: "none",
      background: "#fafafa",
      borderTop: "1px solid #f0f0f0",
      padding: "12px 14px",
      display: "flex",
      alignItems: "center",
      gap: 9,
      justifyContent: "center"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 12,
      color: "#8c8c8c"
    }
  }, "\u041E\u0442\u043F\u0440\u0430\u0432\u043A\u0430 \u0441\u043E\u043E\u0431\u0449\u0435\u043D\u0438\u0439 \u043D\u0435\u0434\u043E\u0441\u0442\u0443\u043F\u043D\u0430")));
}
function Bubble({
  text,
  time
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      justifyContent: "flex-end",
      marginBottom: 10
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: "78%"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      background: "var(--primary)",
      color: "#fff",
      borderRadius: "14px 14px 4px 14px",
      padding: "9px 13px",
      fontSize: 13.5,
      lineHeight: 1.45
    }
  }, text), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 10.5,
      color: "#bfbfbf",
      margin: "3px 4px 0 0",
      textAlign: "right"
    }
  }, time)));
}
function AgentBubble({
  actor,
  initials,
  text,
  meta
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      gap: 8,
      marginBottom: 10
    }
  }, /*#__PURE__*/React.createElement(ActorBadge, {
    actor: actor,
    initials: initials,
    color: "var(--primary)"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: "78%"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      background: "#fff",
      border: "1px solid #eee",
      borderRadius: "14px 14px 14px 4px",
      padding: "9px 13px",
      fontSize: 13.5,
      lineHeight: 1.45,
      color: "#262626"
    }
  }, text), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 10.5,
      color: "#bfbfbf",
      margin: "3px 0 0 4px"
    }
  }, meta)));
}
function QuickReply({
  children
}) {
  return /*#__PURE__*/React.createElement("button", {
    style: {
      padding: "6px 12px",
      borderRadius: 16,
      border: "1px solid var(--primary-border)",
      background: "#f0f7ff",
      color: "#0958d9",
      fontSize: 12,
      fontWeight: 500,
      cursor: "pointer"
    }
  }, children);
}
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/web-chat/WebChatWidget.jsx", error: String((e && e.message) || e) }); }

__ds_ns.CommerceStatusTimeline = __ds_scope.CommerceStatusTimeline;

__ds_ns.DepartmentCard = __ds_scope.DepartmentCard;

__ds_ns.IntegrationHealthCard = __ds_scope.IntegrationHealthCard;

__ds_ns.MetricCard = __ds_scope.MetricCard;

__ds_ns.ProductAIReleaseCard = __ds_scope.ProductAIReleaseCard;

__ds_ns.Avatar = __ds_scope.Avatar;

__ds_ns.Button = __ds_scope.Button;

__ds_ns.Checkbox = __ds_scope.Checkbox;

__ds_ns.Icon = __ds_scope.Icon;

__ds_ns.ICON_NAMES = __ds_scope.ICON_NAMES;

__ds_ns.IconButton = __ds_scope.IconButton;

__ds_ns.Input = __ds_scope.Input;

__ds_ns.Tag = __ds_scope.Tag;

__ds_ns.ConversationInbox = __ds_scope.ConversationInbox;

__ds_ns.KnowledgeDocumentEditor = __ds_scope.KnowledgeDocumentEditor;

__ds_ns.ActorBadge = __ds_scope.ActorBadge;

__ds_ns.AttentionStatus = __ds_scope.AttentionStatus;

__ds_ns.ChannelBadge = __ds_scope.ChannelBadge;

})();
