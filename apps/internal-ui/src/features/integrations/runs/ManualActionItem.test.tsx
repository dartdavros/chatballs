import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { t } from "../../../i18n";
import { schemaField } from "../scenarios/model";
import { ManualActionItem } from "./ManualActionItem";
import type { ManualAction } from "./types";

const action: ManualAction = {
  id: "read-customer", kind: "operation", title: "Find customer", connection: "CRM",
  readOnly: true, parameters: schemaField("", { type: "object" }),
};

describe("manual action row", () => {
  it("renders the service and read-only description below the title", () => {
    const html = renderToStaticMarkup(<ManualActionItem action={action} />);
    expect(html).toContain("<strong>Find customer</strong>");
    expect(html).toContain(`<small>${t("runs.operation")} · CRM · ${t("runs.read_only")}</small>`);
    expect(html).not.toContain("disabled=");
  });

  it("makes unavailable actions disabled and shows their reason inline", () => {
    const html = renderToStaticMarkup(<ManualActionItem action={{ ...action,
      available: false, reason: "Restore service access" }} />);
    expect(html).toContain('disabled=""');
    expect(html).toContain("<small>Restore service access</small>");
  });
});
