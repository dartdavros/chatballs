import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { t } from "../../../i18n";
import { ServiceCardBanners } from "./card/ServiceCardBanners";
import { accessState } from "./model";
import type { ServiceConnection } from "./types";

const connection: ServiceConnection = {
  id: 1, name: "Portal", adapter: "bitrix24", authMethod: "webhook", status: "lost", isActive: true,
  host: "portal.example.test", hasCredentials: true, incompatible: false, lastCheckedAt: null,
  error: null, scenarios: { enabled: 0 }, createdAt: "2026-10-23T00:00:00Z",
};

function banner(item: ServiceConnection) {
  return renderToStaticMarkup(<ServiceCardBanners connection={item} service="Portal" justConnected={false}
    onHide={() => {}} onRestore={() => {}} />);
}

describe("connection check failure presentation", () => {
  it("shows the localized server reason for a DNS error without claiming revoked access", () => {
    const item = { ...connection, error: { code: "address_unresolved", title: "Network title", text: "Network detail" } };
    const html = banner(item);
    expect(html).toContain("Network title");
    expect(html).toContain("Network detail");
    expect(html).not.toContain(t("services.lost_text"));
    expect(html).toContain(t("services.restore"));
    expect(accessState(item, undefined)).toBe("Network title");
  });

  it.each(["invalid_link", "unauthorized", "access_expired", "access_revoked", "crm_access_missing"])("keeps the accepted access recovery state for %s", (code) => {
    const item = { ...connection, error: { code, title: "Access title", text: "Access detail" } };
    expect(banner(item)).toContain(t("services.lost_text"));
    expect(accessState(item, undefined)).toBe(t("services.state_lost"));
  });
});
