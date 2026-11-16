import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it } from "vitest";
import { setPreLoginLanguage } from "../../../i18n";
import { emptyBinding } from "./bindings";
import { ConnectionSetupCard } from "./ConnectionSetupCard";
import { ExternalAgentConnectionFields } from "./ExternalAgentConnectionFields";
import { FeatureCard } from "./FeatureCard";
import { DataPolicyCard } from "./DataPolicyCard";
import { TemplatePolicyCard } from "./TemplatePolicyCard";
import { SettingsSaveFooter } from "./SettingsSaveFooter";
import { SettingsLoadState } from "./SettingsLoadState";
import type { ConnectionDraft, SettingsCatalog } from "./model";

const noop = () => undefined;
const binding = { ...emptyBinding({ id: 1, channelId: 2, name: "Настоящий агент" }, "external"), policyAccepted: true };
const connection: ConnectionDraft = { id: 3, name: "Подключение", baseUrl: "https://service.example.invalid/v1",
  enabled: true, revision: 1, keyConfigured: true, compatible: true, checkedAt: "2026-11-16T00:00:00Z",
  contentTypes: [], bindings: [binding] };
const catalog: SettingsCatalog = { agents: [], sources: [], customFields: [], templates: [] };

function renderConnection(patch: Partial<ConnectionDraft> = {}, state: { retained?: boolean; review?: boolean; failed?: boolean; checking?: boolean } = {}) {
  return renderToStaticMarkup(<ExternalAgentConnectionFields connection={{ ...connection, ...patch }}
    disabled={!!state.retained} retained={!!state.retained} review={!!state.review} failed={!!state.failed}
    checking={!!state.checking} failure="unavailable" dirty={false} accessDirty={false} change={noop} check={noop} keyAction={noop} />);
}

describe("accepted external settings design S01–S03, S20–S39, S72–S73", () => {
  beforeEach(() => setPreLoginLanguage("ru"));

  it("keeps saved keys together before the check and capabilities, including a failed check", () => {
    for (const failed of [false, true]) {
      const html = renderConnection({}, { failed });
      const outgoing = html.indexOf('data-saved-secret="outgoing"');
      const incoming = html.indexOf('data-saved-secret="incoming"');
      const actions = html.indexOf('class="administration-actions"');
      expect(outgoing).toBeGreaterThan(html.indexOf('class="administration-fields"'));
      expect(incoming).toBeGreaterThan(outgoing);
      expect(actions).toBeGreaterThan(incoming);
      expect(html.indexOf("Проверить подключение", actions)).toBeLessThan(html.indexOf("data-capability-result"));
      expect(html).not.toContain("Chatballs → внешний сервис");
      expect(html).not.toContain("Проверка подключения</strong>");
    }
  });

  it("preserves the compact absent-key wrapper in the initial and saved forms", () => {
    const initial = renderToStaticMarkup(<ConnectionSetupCard busy={false} failed={false} save={async () => true} />);
    for (const html of [initial, renderConnection({ keyConfigured: false })]) {
      expect(html).toMatch(/<span data-incoming-key-state="absent"><span class="status-pill/);
      expect(html).toContain("Ключ ещё не создан");
    }
  });

  it("uses retained and review states instead of the initial setup instructions", () => {
    for (const enabled of [false, true]) {
      const html = renderToStaticMarkup(<FeatureCard enabled={enabled} retained review={enabled} busy={false} failed={null} onToggle={noop} />);
      expect(html).toContain("Разрешить внешнее исполнение");
      expect(html).toContain(enabled ? "Прежние полномочия не восстановлены" : "Конфигурация сохранена");
      expect(html).not.toContain("Настройте подключение ниже");
    }
    const retained = renderConnection({}, { retained: true, failed: true });
    expect(retained).toContain("Сохранено");
    expect(retained).not.toContain("Сервис недоступен");
    const disabled = renderConnection({ enabled: false });
    expect(disabled).toContain("Настоящий агент не получает внешние ответы");
    expect(disabled).not.toContain("Помощник продаж");
  });

  it("provides the accepted retry action after enable failure and the full loading/error card", () => {
    const html = renderToStaticMarkup(<SettingsSaveFooter busy={false} failed={false} dirty={false} disabled
      save={noop} enableFailed retryEnable={noop} />);
    expect(html).toContain("Возможность не включена");
    expect(html).toContain("Повторить включение");
    expect(html).not.toContain('disabled=""');
    for (const failed of [false, true]) {
      const load = renderToStaticMarkup(<SettingsLoadState failed={failed} reload={noop} />);
      expect(load).toContain('class="settings-card-head"');
      expect(load).toContain("min-height:440px");
      if (failed) expect(load).toMatch(/class="primary-button"[^>]*>.*Повторить/);
    }
  });

  it("does not mix stale permissions with the empty-policy state", () => {
    const staleBinding = { ...binding, staleGrants: { customFields: [{ sourceConnectionId: 5, fieldId: "old" }], templateIds: ["old-template"] } };
    const props = { name: connection.name, bindings: [staleBinding], binding: staleBinding, catalog, disabled: false, select: noop, change: noop };
    const data = renderToStaticMarkup(<DataPolicyCard {...props} />);
    const templates = renderToStaticMarkup(<TemplatePolicyCard {...props} organization="organization" />);
    expect(data).toContain("Недоступные поля не передаются");
    expect(data).not.toContain("Поля не выбраны");
    expect(templates).toContain("Ранее разрешённый шаблон недоступен");
    expect(templates).not.toContain("Шаблоны не разрешены");
  });
});
