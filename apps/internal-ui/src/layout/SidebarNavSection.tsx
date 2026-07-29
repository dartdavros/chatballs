import { useState } from "react";

import { Icon } from "../shared/icons";
import type { RouteKey } from "../types";

export type SidebarNavSectionItem = {
  activeRoutes: RouteKey[];
  badge?: string;
  disabled?: boolean;
  key: RouteKey;
  label: string;
};

export function SidebarNavSection({
  icon,
  items,
  label,
  route,
  setRoute,
  storageKey,
}: {
  icon: Parameters<typeof Icon>[0]["name"];
  items: SidebarNavSectionItem[];
  label: string;
  route: RouteKey;
  setRoute: (route: RouteKey) => void;
  storageKey: string;
}) {
  const [expanded, setExpanded] = useState(() => {
    try {
      return window.localStorage.getItem(storageKey) === "true";
    } catch {
      return false;
    }
  });
  const active = items.some((item) => item.activeRoutes.includes(route));

  if (items.length === 0) return null;

  function toggleExpanded() {
    setExpanded((current) => {
      const next = !current;
      try {
        window.localStorage.setItem(storageKey, String(next));
      } catch {
        // Навигация остаётся рабочей, даже если хранилище браузера недоступно.
      }
      return next;
    });
  }

  return (
    <div className="hub-nav-section">
      <button
        aria-expanded={expanded}
        className={`hub-nav-item hub-nav-section-toggle ${active ? "is-active" : ""}`}
        type="button"
        onClick={toggleExpanded}
      >
        {active && <span className="active-bar" />}
        <Icon name={icon} />
        {label}
        <span className="hub-nav-chevron"><Icon name="chevron" size={14} /></span>
      </button>
      {expanded && (
        <div className="hub-subnav">
          {items.map((item) => (
            <button
              className={`hub-subnav-item ${item.activeRoutes.includes(route) ? "is-active" : ""}`}
              disabled={item.disabled}
              key={item.key}
              type="button"
              onClick={() => setRoute(item.key)}
            >
              {item.label}
              {item.badge && <b>{item.badge}</b>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
