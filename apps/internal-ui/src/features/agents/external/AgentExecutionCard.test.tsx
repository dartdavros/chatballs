import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it } from "vitest";
import { setPreLoginLanguage } from "../../../i18n";
import { AgentExecutionCard } from "./AgentExecutionCard";
import type { AgentCard } from "../model";

describe("agent external execution visibility", () => {
  beforeEach(() => setPreLoginLanguage("ru"));
  const card = { executionMode: "builtin", externalExecutionEnabled: false, aiStatus: "PAUSED", providerIntegrationId: null } as unknown as AgentCard;
  const render = (value: AgentCard) => renderToStaticMarkup(<AgentExecutionCard card={value} busy={false} canManage apply={async () => true} openSettings={() => undefined} />);
  it("omits external selection before organization opt-in", () => expect(render(card)).toBe(""));
  it("does not claim a return to builtin when it was already selected", () => {
    const html = render({ ...card, externalExecutionEnabled: true });
    expect(html).toContain("Способ исполнения");
    expect(html).not.toContain("Сохранённые настройки восстановлены");
  });
  it("retains the chosen external mode after disabling without a builtin fallback", () => {
    const html = render({ ...card, executionMode: "external", externalExecution: { available: false, connectionId: 2, name: "Saved executor", reason: "disabled" } });
    expect(html).toContain("встроенный ответ автоматически не включён");
    expect(html).toContain("Saved executor");
    expect(html).toContain("disabled");
    expect(html).not.toContain('type="password"');
    expect(html).not.toContain("https://");
  });
});
