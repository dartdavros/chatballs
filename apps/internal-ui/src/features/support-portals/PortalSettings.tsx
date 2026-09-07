import { useEffect, useState } from "react";

import { Icon } from "../../shared/icons";
import {
  listPortalWidgets,
  type PortalAddressConfig,
  type PortalWidgetOption,
  type SupportPortal,
} from "./model";
import { PortalAppearanceSettings } from "./PortalAppearanceSettings";
import { PortalBasicsSettings } from "./PortalBasicsSettings";
import { PortalDomainSettings } from "./PortalDomainSettings";
import { PortalPublishSettings } from "./PortalPublishSettings";
import { PortalWidgetSettings } from "./PortalWidgetSettings";
import {
  PORTAL_SETTINGS_SECTIONS,
  type PortalSettingsSectionKey,
} from "./sections";

// Настройки портала (дизайн-базлайн v2, кадры PT4–PT6): не модалка на 960px с
// пятью секциями подряд, а страница с субменю разделов 250px.

export function PortalSettings({
  address,
  canManage,
  portal,
  section,
  onChanged,
  openSection,
}: {
  address: PortalAddressConfig;
  canManage: boolean;
  portal: SupportPortal;
  section: PortalSettingsSectionKey;
  onChanged: (portal: SupportPortal) => void;
  openSection: (section: PortalSettingsSectionKey) => void;
}) {
  const [anonymousWidgets, setAnonymousWidgets] = useState<PortalWidgetOption[]>([]);

  useEffect(() => {
    listPortalWidgets(portal.id)
      .then((payload) => setAnonymousWidgets(payload.items))
      .catch(() => setAnonymousWidgets([]));
  }, [portal.id]);

  const current = PORTAL_SETTINGS_SECTIONS.find((item) => item.key === section)
    ?? PORTAL_SETTINGS_SECTIONS[0];
  const domainLive = Boolean(portal.customDomain && portal.customDomainVerifiedAt);
  const hints: Partial<Record<PortalSettingsSectionKey, { text: string; tone: "ok" | "muted" }>> = {
    domain: domainLive ? { text: "работает", tone: "ok" } : undefined,
  };

  return (
    <div className="portal-settings-layout">
      <nav className="portal-settings-nav">
        {PORTAL_SETTINGS_SECTIONS.map((item) => (
          <span key={item.key}>
            <button
              className={`portal-settings-nav-item${item.key === current.key ? " is-active" : ""}`}
              type="button"
              onClick={() => openSection(item.key)}
            >
              <Icon name={item.icon} size={16} strokeWidth={1.9} />
              <span>{item.label}</span>
              {hints[item.key] && (
                <small className={hints[item.key]!.tone === "ok" ? "is-ok" : ""}>{hints[item.key]!.text}</small>
              )}
            </button>
            {item.divider && <i className="portal-settings-nav-divider" />}
          </span>
        ))}
        <span className="portal-settings-nav-gap" />
        <p>Изменения применяются к публичным страницам сразу после сохранения.</p>
      </nav>

      <div className="portal-settings-content">
        <div className="portal-settings-inner">
          <div className="portal-settings-heading">
            <h3>{current.heading}</h3>
            <p>{current.lead}</p>
          </div>

          {current.key === "basics" && (
            <PortalBasicsSettings address={address} canManage={canManage} portal={portal} onChanged={onChanged} />
          )}
          {current.key === "domain" && (
            <PortalDomainSettings canManage={canManage} portal={portal} onChanged={onChanged} />
          )}
          {current.key === "theme" && (
            <PortalAppearanceSettings canManage={canManage} portal={portal} onChanged={onChanged} />
          )}
          {current.key === "widget" && (
            <PortalWidgetSettings canManage={canManage} portal={portal} widgets={anonymousWidgets} onChanged={onChanged} />
          )}
          {current.key === "danger" && (
            <PortalPublishSettings canManage={canManage} portal={portal} onChanged={onChanged} />
          )}
        </div>
      </div>
    </div>
  );
}
