import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { t } from "../../../i18n";
import { ManualActionItem } from "./ManualActionItem";
import type { ManualActionSummary } from "./types";

const action: ManualActionSummary = {
  id: "read-customer", kind: "operation", title: "Find customer", connection: "CRM",
  readOnly: true, available: true,
  presentation: { source: { key: "service:1", title: "CRM", subtitle: "Sales", kind: "service" }, categoryPath: [] },
};

describe("manual action row", () => {
  it("renders the service and read-only description below the title", () => {
    const html = renderToStaticMarkup(<ManualActionItem action={action} onSelect={() => {}} />);
    expect(html).toContain("<strong>Find customer</strong>");
    expect(html).toContain(`<small>${t("run_action_picker.operation")} · Sales · ${t("runs.read_only")}</small>`);
    expect(html).not.toContain("disabled=");
    expect(html).not.toContain('tabindex="-1"');
  });

  it("does not reveal an unavailable action or its reason in the employee picker", () => {
    const html = renderToStaticMarkup(<ManualActionItem action={{ ...action,
      available: false, reason: "Restore service access" }} onSelect={() => {}} />);
    expect(html).toBe("");
  });

  it("only selects the row and retains the exact connection identity", () => {
    const selected = vi.fn();
    const row = ManualActionItem({ action, onSelect: selected });
    row!.props.onClick();
    expect(selected).toHaveBeenCalledExactlyOnceWith(action);
  });

  it("highlights matching terms without interpreting action titles as HTML", () => {
    const html = renderToStaticMarkup(<ManualActionItem action={{ ...action, title: "Find <customer>" }} search="customer sales" onSelect={() => {}} />);
    expect(html).toContain("&lt;<mark>customer</mark>&gt;");
    expect(html).toContain("<mark>Sales</mark>");
  });
});
