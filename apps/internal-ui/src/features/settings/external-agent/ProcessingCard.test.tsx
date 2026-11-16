import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { setPreLoginLanguage } from "../../../i18n";
import { emptyBinding } from "./bindings";
import { ProcessingCard } from "./ProcessingCard";

describe("processing settings", () => {
  const binding = emptyBinding({ id: 1, channelId: 2, name: "Agent" }, "executor");
  it("shows the saved mode with the existing field and ru/en translations", () => {
    for (const [language, mode, label] of [["ru", "long", "Долгая обработка"], ["en", "ordinary", "Normal request"]] as const) {
      setPreLoginLanguage(language);
      const html = renderToStaticMarkup(<ProcessingCard binding={{ ...binding, processingMode: mode }}
        connection="Service" disabled={false} change={() => undefined} />);
      expect(html).toContain(label);
      expect(html).not.toContain("external.settings.");
      expect(html).toContain("select-box");
    }
    setPreLoginLanguage("ru");
  });
});
