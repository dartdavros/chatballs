import { t } from "../../i18n";

export type EmailTextParts = {
  latest: string;
  quoted: string;
};

const QUOTE_HEADER_PATTERNS = [
  /^on .+ wrote:\s*$/i,
  /^.+(?:писал|писала|написал|написала):\s*$/i,
  /^-{2,}\s*(?:original message|исходное сообщение)\s*-{2,}$/i,
];

const INLINE_HEADER = /(?:Пн|Вт|Ср|Чт|Пт|Сб|Вс|Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+[^<\n]{1,120}<[^>\n]+>:\s*>?/i;

function quoteOffset(line: string): number {
  const firstContent = line.search(/\S/);
  if (firstContent < 0) return -1;
  const trimmed = line.slice(firstContent);
  if (trimmed.startsWith(">")) return firstContent;
  if (QUOTE_HEADER_PATTERNS.some((pattern) => pattern.test(trimmed))) return firstContent;
  const inlineHeader = line.search(INLINE_HEADER);
  return inlineHeader >= 0 ? inlineHeader : -1;
}

export function splitQuotedEmail(text: string): EmailTextParts {
  const normalized = text.replace(/\r\n?/g, "\n").trim();
  if (!normalized) return { latest: "", quoted: "" };

  const lines = normalized.split("\n");
  for (let index = 0; index < lines.length; index += 1) {
    const offset = quoteOffset(lines[index]);
    if (offset < 0) continue;
    const latestLines = [...lines.slice(0, index), lines[index].slice(0, offset)];
    const quotedLines = [lines[index].slice(offset), ...lines.slice(index + 1)];
    return {
      latest: latestLines.join("\n").trim(),
      quoted: quotedLines.join("\n").trim(),
    };
  }
  return { latest: normalized, quoted: "" };
}

export function foldQuotedHtml(html: string): string {
  const quoteStart = html.toLowerCase().indexOf("<blockquote>");
  if (quoteStart < 0) return html;
  const latest = html.slice(0, quoteStart);
  const quoted = html.slice(quoteStart);
  return `${latest}<details class="email-quoted"><summary>${t("conversations.show_earlier_messages")}</summary>${quoted}</details>`;
}
