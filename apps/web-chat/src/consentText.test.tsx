import { renderToStaticMarkup } from "react-dom/server";
import { beforeAll, describe, expect, it } from "vitest";

import type { WebConfig } from "./api";
import { ChatBody } from "./ChatBody";
import { ConsentText } from "./ConsentText";
import { PreChatForm } from "./PreChatForm";
import { applyWidgetLanguage } from "./i18n";
import { widgetClasses as classes } from "./widgetClasses";

const LINK = '<a href="https://example.ru/privacy" target="_blank" rel="noopener noreferrer nofollow">политику обработки данных</a>';
const RICH = `Нажимая «Начать чат», вы принимаете ${LINK}.<br><strong>Что мы храним:</strong><ul><li>имя и контакты;</li><li>историю диалога.</li></ul>`;
const PLAIN = "Продолжая, вы соглашаетесь на обработку сообщений.";

function config(text: string): WebConfig {
  return { available: true, title: "Помощник", greeting: "Здравствуйте!", consent: { text, version: "v3" } };
}

function screen(text: string): string {
  return renderToStaticMarkup(<ChatBody bodyRef={{ current: null }} config={config(text)} unavailable={false} accepted={false} accent="#1677ff" title="Помощник" messages={[]} pending={[]} awaiting={false} lastContactRequestId={0} showPhoneForm={false} onSubmitContact={async () => true} />);
}

function form(text: string): string {
  return renderToStaticMarkup(<PreChatForm config={{ ...config(text), preChat: { enabled: true, title: "", fields: [] } }} accent="#1677ff" title="Помощник" siteValues={{}} starting={false} onAccept={async () => {}} />);
}

describe("consent text", () => {
  beforeAll(() => applyWidgetLanguage("ru"));

  it("renders the configured text without a revision label", () => {
    for (const text of [PLAIN, RICH]) {
      for (const html of [screen(text), form(text)]) {
        expect(html).toContain(text);
        expect(html).not.toContain("v3");
        expect(html).not.toContain("consent-revision");
      }
    }
  });

  it("renders sanitized markup on the consent screen and in the pre-chat form", () => {
    for (const html of [screen(RICH), form(RICH)]) {
      expect(html).toContain(LINK);
      expect(html).toContain("<br><strong>Что мы храним:</strong><ul><li>имя и контакты;</li>");
      expect(html).not.toContain("&lt;");
    }
  });

  it("renders extra disclosures independently of the configured text", () => {
    const consent = { text: PLAIN, version: "v3", disclosure: "<p>Disclosure</p>" };
    const html = renderToStaticMarkup(<ConsentText consent={consent} />);
    expect(html).toBe(`<div class="${classes.consent}">${PLAIN}</div><div class="${classes.consent}"><p>Disclosure</p></div>`);
  });

  it("goes through one shared component with the form's own spacing hook", () => {
    const shared = renderToStaticMarkup(<ConsentText consent={config(RICH).consent} />);
    expect(screen(RICH)).toContain(shared);
    expect(form(RICH)).toContain(`class="${classes.consent} ${classes.preChatConsent}"`);
  });
});
