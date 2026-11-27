import { formatBytes } from "./chatFormat";
import { t } from "./i18n";
export type BubbleAttachment = { name: string; contentType: string; size: number; available: boolean; url: string; inlineUrl: string };

// Фото догружается после появления пузыря: лента, прижатая к низу, доезжает до него.
function scrollFeedToLatest(event: React.SyntheticEvent<HTMLImageElement>) {
  let node: HTMLElement | null = event.currentTarget.parentElement;
  while (node && !(node.scrollHeight > node.clientHeight && /(auto|scroll)/.test(getComputedStyle(node).overflowY))) node = node.parentElement;
  if (node && node.scrollHeight - node.scrollTop - node.clientHeight < 400) node.scrollTop = node.scrollHeight;
}

export function AttachmentContent({ attachment, text, light }: { attachment: BubbleAttachment; text: string; light: boolean }) {
  const color = light ? "#fff" : "var(--cb-field-text, #262626)";
  const muted = light ? "rgba(255,255,255,.75)" : "var(--cb-muted, #8c8c8c)";
  const image = /^image\/(jpeg|png|gif|webp)$/.test(attachment.contentType) && attachment.inlineUrl;
  return (
    <div>
      {image
        ? <a href={attachment.inlineUrl} target="_blank" rel="noreferrer" style={{ display: "block", borderRadius: 10, overflow: "hidden", maxWidth: 240 }}><img src={attachment.inlineUrl} alt={attachment.name} onLoad={scrollFeedToLatest} style={{ display: "block", width: "100%", maxHeight: 240, objectFit: "cover" }} /></a>
        : (
          <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 200 }}>
            <span style={{ width: 34, height: 34, flex: "none", display: "inline-flex", alignItems: "center", justifyContent: "center", borderRadius: 9, background: light ? "rgba(255,255,255,.2)" : "var(--cb-info-bg, #f0f5ff)", color: light ? "#fff" : "var(--cb-info-text, #1677ff)" }}><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48" /></svg></span>
            <span style={{ display: "flex", flexDirection: "column", minWidth: 0, flex: 1 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{attachment.name}</span>
              <span style={{ fontSize: 11.5, color: muted }}>{attachment.size ? formatBytes(attachment.size) : ""}</span>
            </span>
            {attachment.url ? <a href={attachment.url} download={attachment.name} style={{ fontSize: 12.5, fontWeight: 600, color: light ? "#fff" : "var(--cb-info-text, #1677ff)", textDecoration: "none", flex: "none" }}>{t("chat.download")}</a> : <span style={{ fontSize: 12, color: muted }}>{t("chat.file_unavailable")}</span>}
          </div>
        )}
      {text && <div style={{ marginTop: 6 }}>{text}</div>}
    </div>
  );
}

