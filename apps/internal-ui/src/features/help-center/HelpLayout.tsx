import type { ReactNode } from "react";

import { LogoIcon } from "../../shared/icons";
import { HelpSearch } from "./HelpSearch";
import { PortalWebWidget } from "./PortalWebWidget";
import { SupportLauncher } from "./SupportLauncher";
import type { HelpPortal } from "./types";

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
          <div className="help-products">
            {portal.products.filter((product) => product.siteUrl).map((product) => (
              <a href={product.siteUrl} key={product.code} rel="noreferrer">{product.name}</a>
            ))}
          </div>
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
        <span>База знаний и поддержка</span>
      </footer>
      {portal.webWidgetChannelCode
        ? <PortalWebWidget channelCode={portal.webWidgetChannelCode} />
        : <SupportLauncher products={portal.products} />}
    </div>
  );
}
