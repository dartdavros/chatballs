import { Children, isValidElement, type JSX, type ReactNode } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

export type MarkdownHeading = {
  id: string;
  level: number;
  title: string;
};

type MarkdownBlock =
  | { kind: "heading"; level: number; text: string; id: string }
  | { kind: "paragraph"; text: string }
  | { kind: "list"; ordered: boolean; items: string[] }
  | { kind: "code"; text: string };

function headingId(text: string, index: number): string {
  const normalized = text
    .toLocaleLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, "-")
    .replace(/^-+|-+$/g, "");
  return normalized || `section-${index + 1}`;
}

function plainHeadingText(text: string): string {
  return text
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/[*_~`]/g, "")
    .trim();
}

function uniqueHeadingId(
  text: string,
  index: number,
  occurrences: Map<string, number>,
): string {
  const baseId = headingId(text, index);
  const occurrence = (occurrences.get(baseId) ?? 0) + 1;
  occurrences.set(baseId, occurrence);
  return occurrence === 1 ? baseId : `${baseId}-${occurrence}`;
}

export function parseMarkdown(content: string): {
  blocks: MarkdownBlock[];
  headings: MarkdownHeading[];
} {
  const lines = content.replace(/\r\n/g, "\n").split("\n");
  const blocks: MarkdownBlock[] = [];
  const headings: MarkdownHeading[] = [];
  const headingIds = new Map<string, number>();
  let index = 0;
  let inCodeFence = false;
  let code: string[] = [];

  while (index < lines.length) {
    const sourceLine = lines[index];
    const line = sourceLine.trim();
    if (line.startsWith("```") || line.startsWith("~~~")) {
      if (inCodeFence) {
        blocks.push({ kind: "code", text: code.join("\n") });
        code = [];
      }
      inCodeFence = !inCodeFence;
      index += 1;
      continue;
    }
    if (inCodeFence) {
      code.push(sourceLine);
      index += 1;
      continue;
    }
    const heading = line.match(/^(#{1,6})\s+(.+?)\s*#*$/);
    if (heading) {
      const level = Math.min(6, Math.max(2, heading[1].length));
      const title = plainHeadingText(heading[2]);
      const id = uniqueHeadingId(title, headings.length, headingIds);
      blocks.push({ kind: "heading", level, text: title, id });
      headings.push({ id, level, title });
    } else if (line) {
      blocks.push({ kind: "paragraph", text: line });
    }
    index += 1;
  }
  if (code.length) blocks.push({ kind: "code", text: code.join("\n") });
  return { blocks, headings };
}

function nodeText(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(nodeText).join("");
  if (isValidElement<{ children?: ReactNode }>(node)) {
    return nodeText(node.props.children);
  }
  return "";
}

export function MarkdownContent({ content }: { content: string }) {
  const headingIds = new Map<string, number>();
  let headingIndex = 0;
  const heading = (level: number) => {
    const Heading = ({ children }: { children?: ReactNode }) => {
      const id = uniqueHeadingId(nodeText(Children.toArray(children)), headingIndex, headingIds);
      headingIndex += 1;
      const Tag = `h${Math.min(6, Math.max(2, level))}` as keyof JSX.IntrinsicElements;
      return <Tag id={id}>{children}</Tag>;
    };
    return Heading;
  };
  const components: Components = {
    h1: heading(2),
    h2: heading(2),
    h3: heading(3),
    h4: heading(4),
    h5: heading(5),
    h6: heading(6),
    a: ({ children, href }) => <a className="link" href={href}>{children}</a>,
  };

  return (
    <div className="help-markdown">
      <ReactMarkdown components={components} remarkPlugins={[remarkGfm]}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
