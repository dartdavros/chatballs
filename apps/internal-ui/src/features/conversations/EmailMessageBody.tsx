import { useMemo } from "react";

import { foldQuotedHtml, splitQuotedEmail } from "./emailContent";

const DOCUMENT_START = `<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; base-uri 'none'; form-action 'none'; img-src data:; style-src 'unsafe-inline'">
  <meta name="referrer" content="no-referrer">
  <style>
    :root { color-scheme: light; }
    body { margin: 0; color: #262626; background: #fff; font: 13.5px/1.5 Arial, sans-serif; overflow-wrap: anywhere; }
    p, ul, ol, blockquote, pre, table { margin: 0 0 10px; }
    p:last-child, ul:last-child, ol:last-child, blockquote:last-child, pre:last-child, table:last-child { margin-bottom: 0; }
    blockquote { margin-left: 0; padding-left: 12px; color: #595959; border-left: 3px solid #d9d9d9; }
    pre { padding: 8px; background: #f5f5f5; white-space: pre-wrap; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 5px 7px; border: 1px solid #d9d9d9; text-align: left; vertical-align: top; }
    a { color: #1677ff; }
    details.email-quoted { margin-top: 10px; color: #595959; }
    details.email-quoted > summary { color: #8c8c8c; cursor: pointer; user-select: none; }
    details.email-quoted > blockquote { margin-top: 8px; }
  </style>
</head>
<body>`;

export function EmailMessageBody({ html, text }: { html?: string; text: string }) {
  const textParts = useMemo(() => splitQuotedEmail(text), [text]);
  const srcDoc = useMemo(
    () => `${DOCUMENT_START}${foldQuotedHtml(html ?? "")}</body></html>`,
    [html],
  );
  if (!html) {
    return (
      <div className="sales-email-plain">
        {textParts.latest && <div>{textParts.latest}</div>}
        {textParts.quoted && (
          <details className="sales-email-quoted">
            <summary>Показать предыдущие сообщения</summary>
            <div>{textParts.quoted}</div>
          </details>
        )}
      </div>
    );
  }
  return (
    <iframe
      className="sales-email-body-frame"
      referrerPolicy="no-referrer"
      sandbox=""
      srcDoc={srcDoc}
      title="Содержимое письма"
    />
  );
}
