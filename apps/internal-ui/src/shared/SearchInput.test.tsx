import { setCurrentLanguage } from "@chatballs/shared";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it } from "vitest";

import { SearchInput } from "./ui-controls";
import { HelpSearch } from "../features/help-center/HelpSearch";

beforeEach(() => { setCurrentLanguage("ru"); });

describe("shared search hint", () => {
  it("shows the chat shortcut by default with an accessible search label", () => {
    const html = renderToStaticMarkup(<SearchInput placeholder="Поиск действий" value="" />);
    expect(html).toContain('aria-label="Поиск действий"');
    expect(html).toContain('aria-keyshortcuts="/"');
    expect(html).toContain('<kbd class="ui-search-shortcut" aria-hidden="true">/</kbd>');
  });

  it("preserves the clear button when a search has a value", () => {
    const html = renderToStaticMarkup(<SearchInput placeholder="Поиск" value="CRM" clearable />);
    expect(html).toContain('aria-label="Очистить поиск"');
    expect(html).toContain('value="CRM"');
    expect(html).not.toContain("<kbd");
  });

  it("does not advertise a shortcut while its input is disabled", () => {
    const html = renderToStaticMarkup(<SearchInput placeholder="Поиск" disabled />);
    expect(html).toContain('disabled=""');
    expect(html).not.toContain("aria-keyshortcuts");
    expect(html).not.toContain("<kbd");
  });

  it("uses the same hint for both public portal search variants", () => {
    for (const compact of [true, false]) {
      const html = renderToStaticMarkup(<HelpSearch value="" compact={compact} onChange={() => undefined} />);
      expect(html).toContain('type="search"');
      expect(html).toContain('aria-keyshortcuts="/"');
      expect(html).toContain('<kbd class="ui-search-shortcut" aria-hidden="true">/</kbd>');
    }
  });
});
