import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { t } from "../i18n";
import { DictationStatus, type ComposerDictation } from "./DictationStatus";

function dictation(notice: ComposerDictation["notice"]): ComposerDictation {
  return {
    notice, recording: notice === "recording", busy: ["permission", "recording", "recognizing"].includes(notice ?? ""),
    seconds: 2, limit: null, retryable: false, available: true, maxSeconds: 60, maxBytes: 10485760,
    start: vi.fn(), stop: vi.fn(), cancel: vi.fn(), retry: vi.fn(),
  };
}

describe("dictation panel visibility", () => {
  it("keeps a closed panel hidden even when the retained draft exceeds the send limit", () => {
    for (const tooLong of [false, true]) {
      expect(renderToStaticMarkup(<DictationStatus dictation={dictation(null)} tooLong={tooLong} />)).toBe("");
    }
  });

  it.each(["permission", "recording", "recognizing", "result", "cancelled", "denied", "networkError"] as const)(
    "offers close in the %s state", (notice) => {
      const html = renderToStaticMarkup(<DictationStatus dictation={dictation(notice)} tooLong={false} />);
      expect(html).toContain('role="status"');
      expect(html).toContain(`aria-label="${t("speech.cancel")}"`);
      expect(html.includes("wc-dictation-stop")).toBe(notice === "recording");
    },
  );
});
