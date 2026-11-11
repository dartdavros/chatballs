import { renderToStaticMarkup } from "react-dom/server";
import { afterAll, describe, expect, it, vi } from "vitest";

import { t } from "../../i18n";
import type { SessionUser } from "../../types";
import { visibleSettingsGroups } from "./navigation";
import { settingsSectionKey, visibleSettingsSections } from "./sections";
import { SettingsNavigation } from "./SettingsNavigation";

vi.hoisted(() => {
  vi.stubGlobal("window", { location: { origin: "https://example.test" } });
});
afterAll(() => vi.unstubAllGlobals());

const user = { role: "ADMIN", isInstanceAdmin: false } as SessionUser;

describe("settings navigation", () => {
  it.each([false, true])("keeps every permitted section exactly once (instance admin: %s)", isInstanceAdmin => {
    const current = { ...user, isInstanceAdmin };
    const keys = visibleSettingsGroups(current).flatMap(group => group.sections.map(section => section.key));
    expect(keys.length).toBe(new Set(keys).size);
    expect([...keys].sort()).toEqual(visibleSettingsSections(current).map(section => section.key).sort());
    expect(visibleSettingsGroups(current).map(group => group.key)).toEqual(["organization", "service", "quality", "other"]);
    for (const key of ["ai", "integrations", "scenarios", "skills"]) expect(keys).not.toContain(key);
  });

  it("keeps organization counts and audit without the promoted destinations", () => {
    const html = renderToStaticMarkup(<SettingsNavigation user={user} active="groups" hidden={false}
      counts={{ groups: 2, templates: 3 }} openSection={() => undefined} setRoute={() => undefined} />);
    expect(html).toContain(`${t("common.groups")}</span><small>2</small>`);
    expect(html).toContain(`${t("settings.reply_templates")}</span><small>3</small>`);
    expect(html).toContain('aria-current="page"');
    expect(html).not.toContain(t("settings.ai_provider"));
    expect(html).not.toContain(t("common.integrations"));
    expect(html).not.toContain(t("scenarios.title"));
    expect(html).not.toContain(t("skills.title"));
    expect(html).not.toContain(t("settings.file_storage"));
    expect(html).not.toContain(t("settings.platform"));
    expect(html).toContain(t("settings.action_audit"));
  });

  it("keeps installation settings restricted and their onboarding target available", () => {
    const html = renderToStaticMarkup(<SettingsNavigation user={{ ...user, isInstanceAdmin: true }} active="platform" hidden={false}
      counts={{}} openSection={() => undefined} setRoute={() => undefined} />);
    expect(html).toContain(t("settings.file_storage"));
    expect(html).toContain(t("settings.platform"));
    expect(html).toContain('data-onboarding-target="settings-platform"');
  });

  it("hides the section list when a settings page is open on mobile", () => {
    const html = renderToStaticMarkup(<SettingsNavigation user={user} active="organization" hidden
      counts={{}} openSection={() => undefined} setRoute={() => undefined} />);
    expect(html).toContain('settings-subnav is-hidden');
  });

  it.each(["ai", "integrations", "scenarios", "skills"])("no longer accepts %s as a settings section", key => {
    expect(settingsSectionKey(key)).toBeNull();
  });
});
