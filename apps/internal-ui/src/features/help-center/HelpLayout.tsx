import type { ReactNode } from "react";

import { LogoIcon } from "../../shared/icons";
import { HelpSearch } from "./HelpSearch";
import { PortalWebWidget } from "./PortalWebWidget";
import type { HelpPortal } from "./types";
import { t } from "../../i18n";

export function HelpLayout({
  portal,
  children,
  search,
  onSearchChange,
  onSearchSubmit,
  compactHeader = false,
}: {
  portal: HelpPortal;
  children: ReactNode;
  search: string;
  onSearchChange: (value: string) => void;
  onSearchSubmit?: (value: string) => void;
  compactHeader?: boolean;
}) {
  const homeHref = "/";
  return (
    <div className={`help-center ${compactHeader ? "has-compact-header" : ""}`}>
      <header className="help-header">
        <div className="help-header-row">
          <a className="help-brand" href={homeHref}>
            <span className="help-brand-mark"><LogoIcon /></span>
            <span>{portal.name}</span>
          </a>
        </div>
        {compactHeader && (
          <HelpSearch
            compact
            value={search}
            onChange={onSearchChange}
            onSubmit={onSearchSubmit}
          />
        )}
      </header>
      <main>{children}</main>
      <footer className="help-footer">
        <a className="help-footer-brand" href={homeHref}>
          <span className="help-brand-mark"><LogoIcon /></span>
          <span>{portal.name}</span>
        </a>
        <span>{t("portals.knowledge_base_support")}</span>
      </footer>
      {portal.webWidgetKey && <PortalWebWidget widgetKey={portal.webWidgetKey} />}
    </div>
  );
}
