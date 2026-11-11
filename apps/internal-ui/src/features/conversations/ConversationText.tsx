import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import "./conversation-text.css";

export type ConversationTextSyntax = "markdown" | "telegram";

type MarkdownNode = {
  type: string;
  position?: { start?: { offset?: number } };
  children?: MarkdownNode[];
  data?: Record<string, unknown>;
};

// Telegram uses *bold*, _italic_ and __underline__, unlike CommonMark's
// *italic* and __bold__. Adjust the parsed nodes, never the raw message:
// replacements on strings would also corrupt links, code and escaped markers.
function telegramFormatting() {
  return (tree: MarkdownNode, file: { value: unknown }) => {
    const source = String(file.value ?? "");
    const visit = (node: MarkdownNode): void => {
      const offset = node.position?.start?.offset;
      if (typeof offset === "number") {
        if (node.type === "emphasis" && source[offset] === "*") node.type = "strong";
        if (node.type === "strong" && source.slice(offset, offset + 2) === "__") {
          node.data = { ...node.data, hName: "u" };
        }
      }
      node.children?.forEach(visit);
    };
    visit(tree);
  };
}

const markdownPlugins = [remarkGfm];
const telegramPlugins = [remarkGfm, telegramFormatting];

const allowedElements = [
  "a", "p", "br", "strong", "em", "del", "u", "code", "pre",
  "blockquote", "ul", "ol", "li", "img",
];

function safeMessageUrl(value: string): string {
  try {
    const url = new URL(value);
    return ["https:", "http:", "mailto:", "tel:"].includes(url.protocol) ? url.href : "";
  } catch {
    return "";
  }
}

const components: Components = {
  a: ({ href, children }) => href
    ? <a className="link" href={href} target="_blank" rel="noopener noreferrer">{children}</a>
    : <span>{children}</span>,
  // Markdown text can mention an image, but never load untrusted remote
  // media into the operator interface. Attachments have their own renderer.
  img: ({ alt }) => <span>{alt}</span>,
};

export function ConversationText({ text, syntax = "markdown" }: {
  text: string;
  syntax?: ConversationTextSyntax;
}) {
  return (
    <div className="conversation-text">
      <ReactMarkdown
        remarkPlugins={syntax === "telegram" ? telegramPlugins : markdownPlugins}
        allowedElements={allowedElements}
        unwrapDisallowed
        urlTransform={safeMessageUrl}
        components={components}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
