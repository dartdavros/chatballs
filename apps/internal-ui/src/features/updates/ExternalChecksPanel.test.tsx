import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ExternalChecksPanel } from "./ExternalChecksPanel";

describe("service announcements", () => {
  it("preserves order and plain text and only renders safe links", () => {
    const html = renderToStaticMarkup(
      <ExternalChecksPanel enabled saving={false} saveFailed={false} failed={false} toggle={async () => undefined}
        announcements={[
          { id: 1, title: "<b>Первое</b>", text: "Раз.\n\nДва.", link: "https://example.org/" },
          { id: 2, title: "Второе", text: "Текст", link: "https://user@example.org/" },
          { id: 3, title: "Третье", text: "Текст", link: "" },
          { id: 4, title: "Четвёртое", text: "Текст", link: "javascript:alert(1)" },
        ]}
      />,
    );
    expect(html.indexOf("&lt;b&gt;Первое&lt;/b&gt;")).toBeLessThan(html.indexOf("Второе"));
    expect(html).not.toContain("<b>Первое</b>");
    expect(html).toContain("Раз.\n\nДва.");
    expect(html.match(/href="[^"]*"/g)).toEqual(['href="https://example.org/"']);
  });
});
