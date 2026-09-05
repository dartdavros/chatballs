import { describe, expect, it } from "vitest";

import { supportHref } from "./SupportLauncher";

describe("supportHref", () => {
  it("passes the selected support channel to the product", () => {
    expect(supportHref({
      code: "acme",
      name: "Acme",
      siteUrl: "https://acme.example/account?from=help",
      supportAvailable: true,
      supportWidgetKey: "wgt_acme_support",
      supportChannelCode: "acme-support",
    })).toBe("https://acme.example/account?from=help&chatballsSupportWidget=wgt_acme_support");
  });

  it("does not build an unauthenticated fallback without a channel", () => {
    expect(supportHref({
      code: "acme",
      name: "Acme",
      siteUrl: "https://acme.example",
      supportAvailable: false,
      supportChannelCode: null,
      supportWidgetKey: null,
    })).toBeNull();
  });
});
