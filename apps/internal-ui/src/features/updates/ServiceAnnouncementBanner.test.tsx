import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ServiceAnnouncementBanner } from "./ServiceAnnouncementBanner";

describe("service announcement banner", () => {
  it("renders only the first message with plain text, paragraph breaks and its link", () => {
    const html = renderToStaticMarkup(
      <ServiceAnnouncementBanner
        announcements={[
          { id: 20, title: "<b>Первое</b>", text: "Раз.\n\nДва.", link: "https://example.org/" },
          { id: 10, title: "Второе", text: "Текст", link: "" },
        ]}
        onDismissLast={() => undefined}
      />,
    );
    expect(html).toContain("&lt;b&gt;Первое&lt;/b&gt;");
    expect(html).not.toContain("Второе");
    expect(html).toContain("Раз.\n\nДва.");
    expect(html.match(/href="[^"]*"/g)).toEqual(['href="https://example.org/"']);
  });

  it.each(["", "//example.org", "javascript:alert(1)", "https://user@example.org/", "https://@example.org/"])(
    "omits an inadmissible publication link (%s)",
    (link) => {
      const html = renderToStaticMarkup(
        <ServiceAnnouncementBanner
          announcements={[{ id: 1, title: "Заголовок", text: "Текст", link }]}
          onDismissLast={() => undefined}
        />,
      );
      expect(html).not.toContain("href=");
    },
  );

  it("renders no banner for a missing or empty snapshot", () => {
    for (const announcements of [null, []]) {
      expect(renderToStaticMarkup(
        <ServiceAnnouncementBanner announcements={announcements} onDismissLast={() => undefined} />,
      )).toBe("");
    }
  });
});
