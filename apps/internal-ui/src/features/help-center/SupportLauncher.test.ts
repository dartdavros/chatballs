import { describe, expect, it } from "vitest";

import { supportHref } from "./SupportLauncher";

describe("supportHref", () => {
  it("passes the selected support channel to the product", () => {
    expect(supportHref({
      code: "foxray",
      name: "Foxray",
      siteUrl: "https://foxray.example/account?from=help",
      supportAvailable: true,
      supportWidgetKey: "wgt_foxray_support",
      supportChannelCode: "foxray-support",
    })).toBe("https://foxray.example/account?from=help&chatbollsSupportWidget=wgt_foxray_support");
  });

  it("does not build an unauthenticated fallback without a channel", () => {
    expect(supportHref({
      code: "foxray",
      name: "Foxray",
      siteUrl: "https://foxray.example",
      supportAvailable: false,
      supportChannelCode: null,
      supportWidgetKey: null,
    })).toBeNull();
  });
});
