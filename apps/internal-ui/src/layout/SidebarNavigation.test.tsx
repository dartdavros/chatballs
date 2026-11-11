import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { Role, RouteKey, SessionUser } from "../types";
import { t } from "../i18n";
import { HELP_CENTER_URL, helpArticleUrl } from "../shared/help";
import { SidebarNavigation } from "./SidebarNavigation";
import { Sidebar } from "./Sidebar";
import { RealtimeProvider } from "../features/realtime/RealtimeProvider";

// SSR проверяет именно видимость пунктов: эффекты обновления сессии и API
// здесь не выполняются, состояние аккаунтов штатного контура не меняется.
function userWith(role: Role, reportCapabilities: string[] = []) {
  const user: SessionUser = {
    id: 1, email: "user@example.test", fullName: "User", mustChangePassword: false,
    totpEnabled: false, totpLastUsedAt: null, deliveryMode: "CLOUD", isInstanceAdmin: false,
    uiTheme: "SYSTEM", uiAccent: "", uiLanguage: "", language: "ru", memberships: [],
    organizationPublicId: "org", organization: "org", organizationName: "Org",
    organizationLogoUrl: null, role, positionTitle: "", totpRequired: false,
    capabilities: [], groups: [], joinedAt: "2026-01-01T00:00:00Z", reportCapabilities,
  };
  return user;
}

function render(role: Role, reportCapabilities: string[] = [], route: RouteKey = "chat") {
  const user = userWith(role, reportCapabilities);
  return renderToStaticMarkup(
    <SidebarNavigation route={route} user={user} setRoute={() => undefined} waitingCount={0}
      chatScope={{ kind: "all" }} setChatScope={() => undefined} chatCounters={null} />,
  );
}

describe("sidebar navigation", () => {
  it.each(["OWNER", "ADMIN"] as const)("shows the approved five groups with direct destinations for %s", (role) => {
    const html = render(role);
    const labels = ["common.chat", "common.contacts", "reports.title", "common.agents", "skills.title", "scenarios.title", "navigation.ai_providers", "navigation.tools", "common.knowledge_base", "common.portals", "navigation.widgets", "navigation.messengers", "navigation.mail", "common.integrations", "common.operators", "common.settings", "navigation.help"] as const;
    const positions = labels.map((key) => html.indexOf(renderToStaticMarkup(<span>{t(key)}</span>)));
    expect(positions.every((position) => position >= 0)).toBe(true);
    expect(positions).toEqual([...positions].sort((a, b) => a - b));
    const navigation = html.slice(0, html.indexOf("</nav>"));
    const dividers = [...navigation.matchAll(/class="hub-nav-divider"/g)].map(match => match.index!);
    expect(dividers).toHaveLength(4);
    for (const [divider, boundary] of dividers.map((position, index) => [position, [2, 7, 9, 13][index]])) {
      expect(divider).toBeGreaterThan(positions[boundary]);
      expect(divider).toBeLessThan(positions[boundary + 1]);
    }
    expect(html).toContain('data-onboarding-target="nav-ai-providers"');
    expect(html).toContain('data-onboarding-target="nav-widgets"');
    expect(html).toContain('data-onboarding-target="nav-messengers"');
    expect(html.indexOf('class="hub-sidebar-help"')).toBeGreaterThan(html.indexOf("</nav>"));
  });

  it.each([
    ["skills", "skills.title"],
    ["agents", "common.agents"],
    ["agentDetail", "common.agents"],
    ["scenarios", "scenarios.title"],
    ["aiProviders", "navigation.ai_providers"],
    ["webIntegrationSettings", "navigation.widgets"],
    ["messengers", "navigation.messengers"],
    ["emailIntegrations", "navigation.mail"],
    ["externalServerSettings", "navigation.tools"],
    ["mcpServerCreate", "navigation.tools"],
    ["httpServerCreate", "navigation.tools"],
    ["serviceConnection", "common.integrations"],
    ["qualityAnalysis", "reports.title"],
    ["ruleJournal", "common.settings"],
    ["administrationAudit", "common.settings"],
  ] as const)("highlights the owning menu item on %s", (route, label) => {
    const html = render("ADMIN", [], route);
    const active = [...html.matchAll(/<button class="hub-nav-item is-active"[^>]*>(.*?)<\/button>/g)];
    expect(active).toHaveLength(1);
    expect(active[0][0]).toContain('aria-current="page"');
    expect(active[0][1]).toContain(renderToStaticMarkup(<span>{t(label)}</span>));
  });

  it.each(["EMPLOYEE", "SUPERVISOR"] as const)("shows help after the tree and statistics only with the grant for %s", (role) => {
    for (const allowed of [false, true]) {
      const html = render(role, allowed ? ["reports.view"] : []);
      expect(html.includes(`<span>${t("reports.title")}</span>`)).toBe(allowed);
      expect(html).not.toContain(`<span>${t("common.settings")}</span>`);
      expect(html).not.toContain(`<span>${t("skills.title")}</span>`);
      expect(html).not.toContain(`<span>${t("navigation.ai_providers")}</span>`);
      expect(html).not.toContain(`<span>${t("navigation.widgets")}</span>`);
      expect(html.indexOf('class="hub-sidebar-help"')).toBeGreaterThan(html.indexOf("</nav>"));
      expect(html.indexOf('class="hub-nav-divider"')).toBeLessThan(html.indexOf(`<span>${t("navigation.help")}</span>`));
      if (allowed) expect(html.indexOf(`<span>${t("reports.title")}</span>`)).toBeLessThan(html.indexOf(`<span>${t("navigation.help")}</span>`));
    }
  });

  it.each(["profile", "replyTemplates"] as const)("keeps the employee sidebar free of conversation navigation on %s", route => {
    expect(render("EMPLOYEE", [], route)).toBe("");
  });

  it("uses a native safe help link and preserves article URLs", () => {
    const html = render("EMPLOYEE");
    expect(html).toContain(`href="${HELP_CENTER_URL}" target="_blank" rel="noopener noreferrer"`);
    expect(html).toContain(`title="${t("navigation.help_tooltip")}"`);
    expect(helpArticleUrl("agent")).toBe(`${HELP_CENTER_URL}articles/agent`);
  });

  it("keeps an organization logo in both the rail and full menu", () => {
    const logoUrl = "/api/v1/organizations/org/logo/";
    const html = renderToStaticMarkup(
      <RealtimeProvider><Sidebar route="chat" user={{ ...userWith("ADMIN"), organizationLogoUrl: logoUrl }}
        setRoute={() => undefined} onLogout={() => undefined} onSwitchOrganization={() => undefined}
        chatScope={{ kind: "all" }} setChatScope={() => undefined} chatCounters={null}
        expanded={false} setExpanded={() => undefined} /></RealtimeProvider>,
    );
    expect(html.match(new RegExp(`src="${logoUrl}"`, "g"))).toHaveLength(2);
    expect(html).not.toContain('class="chatballs-logo"');
    expect(html.match(/hub-brand-mark has-logo/g)).toHaveLength(2);
    expect(html.indexOf('class="hub-sidebar-help"')).toBeLessThan(html.indexOf('class="profile-link'));
  });
});
