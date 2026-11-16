import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it } from "vitest";
import { setPreLoginLanguage } from "../../i18n";
import { withExternalNotices } from "./externalFeed";
import { ConversationMessage } from "./ConversationMessage";
import type { ApiMessage } from "./apiTypes";
import type { ConversationListItem } from "./types";

describe("external conversation delivery truth", () => {
  beforeEach(() => setPreLoginLanguage("ru"));
  const message: ApiMessage = { id: 1, author: "AI", text: "Actual stored answer", createdAt: "2026-11-16T09:00:00Z",
    externalDelivery: { state: "unknown", textFallback: false, initiative: false } };
  const dialog = { id: 1, channel: "TG", agentName: "Agent", agentColor: "blue" } as unknown as ConversationListItem;
  const render = (item: ApiMessage) => renderToStaticMarkup(<ConversationMessage message={item} dialog={dialog} viewerId={null} />);
  it("shows the actual uncertain message without a success mark and hides suppressed content", () => {
    const html = render(message);
    expect(html).toContain("Actual stored answer");
    expect(html).toContain("Отправка не подтверждена");
    expect(html).not.toContain('M20 6 9 17l-5-5');
    expect(render({ ...message, externalDelivery: { ...message.externalDelivery!, state: "transport_accepted" } })).toContain('M20 6 9 17l-5-5');
    expect(render({ ...message, externalDelivery: { ...message.externalDelivery!, state: "suppressed" } })).toBe("");
  });
  it("orders scoped notices with messages without exposing unloaded older history", () => {
    const rows = [{ key: "m1", createdAt: "2026-11-16T09:00:00Z" }];
    expect(withExternalNotices(rows, [
      { id: "old", kind: "handoff", summary: "", createdAt: "2026-11-15T09:00:00Z" },
      { id: "new", kind: "unknown", summary: "", createdAt: "2026-11-16T09:01:00Z" },
    ], true).map(row => row.key)).toEqual(["m1", "external:new"]);
  });
});
