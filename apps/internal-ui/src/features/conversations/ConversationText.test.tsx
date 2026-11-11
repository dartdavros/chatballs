import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ConversationText } from "./ConversationText";

const render = (text: string, syntax: "markdown" | "telegram" = "markdown") =>
  renderToStaticMarkup(<ConversationText text={text} syntax={syntax} />);

describe("conversation rich-text rendering", () => {
  it("links bare URLs, named links and email addresses without changing hashtags", () => {
    const html = render("See https://ru.pirates.travel/flight and [для iOS](https://p.irat.es/apple)\n#Авиабилеты");
    expect(html).toContain('href="https://ru.pirates.travel/flight"');
    expect(html).toContain('href="https://p.irat.es/apple"');
    expect(html).toContain(">для iOS</a>");
    expect(html).toContain('target="_blank"');
    expect(html).toContain('rel="noopener noreferrer"');
    expect(html).toContain("#Авиабилеты");
  });

  it("preserves incoming newlines and paragraph separation", () => {
    const html = render("Первая строка\nВторая строка\n\nТретий абзац");
    expect(html).toContain("Первая строка\nВторая строка");
    expect(html).toContain("<p>Третий абзац</p>");
    expect(html).toContain('class="conversation-text"');
  });

  it("supports CommonMark and GFM formatting outside Telegram", () => {
    const html = render("**жирный** *курсив* ~~зачёркнутый~~ `код`\n\n> цитата\n\n- первый\n- второй");
    expect(html).toContain("<strong>жирный</strong>");
    expect(html).toContain("<em>курсив</em>");
    expect(html).toContain("<del>зачёркнутый</del>");
    expect(html).toContain("<code>код</code>");
    expect(html).toContain("<blockquote>");
    expect(html).toContain("<ul>");
  });

  it("supports Telegram asterisk-bold, underscore-italic, underline and strike", () => {
    const html = render("*Жирный* _курсив_ __подчёркнутый__ ~зачёркнутый~", "telegram");
    expect(html).toContain("<strong>Жирный</strong>");
    expect(html).toContain("<em>курсив</em>");
    expect(html).toContain("<u>подчёркнутый</u>");
    expect(html).toContain("<del>зачёркнутый</del>");
  });

  it("does not execute HTML, follow unsafe URLs, or fetch markdown images", () => {
    const html = render('<script>alert(1)</script> [click](javascript:alert%281%29) ![track](https://tracker.example/pixel.png)');
    expect(html).not.toContain("<script");
    expect(html).not.toContain('href="javascript:');
    expect(html).not.toContain("<img");
    expect(html).toContain("click");
  });

  it("keeps literal code separate from Telegram markup", () => {
    const html = render("`*not bold*` and *bold*", "telegram");
    expect(html).toContain("<code>*not bold*</code>");
    expect(html).toContain("<strong>bold</strong>");
  });
});
