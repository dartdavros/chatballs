import { describe, expect, it } from "vitest";

import { surfaceForHost } from "./surface";

describe("surfaceForHost", () => {
  it("keeps the configured application host on the application surface", () => {
    expect(surfaceForHost("app.localhost")).toBe("app");
    expect(surfaceForHost("app.example.com", "app.example.com")).toBe("app");
  });

  it("routes hosted help domains independently of their path", () => {
    expect(surfaceForHost("docs.localhost")).toBe("help");
    expect(surfaceForHost("docs.help.custocrm.ru")).toBe("help");
  });

  it("probes unknown hosts so verified custom domains can resolve", () => {
    expect(surfaceForHost("help.customer.example")).toBe("loading");
  });
});
