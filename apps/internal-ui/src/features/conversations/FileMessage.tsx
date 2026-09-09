import { useState, type SyntheticEvent } from "react";

import { Icon } from "../../shared/icons";
import { ImageLightbox } from "./ImageLightbox";
import { resolveApiUrl } from "../../api/client";
import { formatSize } from "../ai/knowledge/model";
import { isImageAttachment, type ApiMessage } from "./model";
import { t } from "../../i18n";

// Файл или фото в ленте: фото — превью со ссылкой на оригинал, остальное —
// карточка с именем, размером и ссылкой «Скачать» (единый `.link`).

// Фото догружается после появления пузыря: лента, прижатая к низу, доезжает до него.
function scrollFeedToLatest(event: SyntheticEvent<HTMLImageElement>) {
  let node: HTMLElement | null = event.currentTarget.parentElement;
  while (node && !(node.scrollHeight > node.clientHeight && /(auto|scroll)/.test(getComputedStyle(node).overflowY))) node = node.parentElement;
  if (node && node.scrollHeight - node.scrollTop - node.clientHeight < 400) node.scrollTop = node.scrollHeight;
}

export function FileMessage({ message }: { message: ApiMessage }) {
  const [lightbox, setLightbox] = useState(false);
  const url = message.attachmentUrl ? resolveApiUrl(message.attachmentUrl) : "";
  const name = message.attachmentName || t("conversations.file");
  if (!url) {
    return <span className="file-message-missing">{t("conversations.file_unavailable", { name })}</span>;
  }
  const image = isImageAttachment(message);
  return (
    <div className={`file-message${image ? " is-image" : ""}`}>
      {image
        ? (
          <>
            <button className="file-message-image" type="button" title={name} onClick={() => setLightbox(true)}>
              <img src={`${url}?inline`} alt={name} onLoad={scrollFeedToLatest} />
            </button>
            <ImageLightbox open={lightbox} url={`${url}?inline`} downloadUrl={url} name={name} size={message.attachmentSize} onClose={() => setLightbox(false)} />
          </>
        )
        : (
          <div className="file-message-card">
            <span className="file-message-icon"><Icon name="paperclip" size={16} /></span>
            <div className="file-message-meta">
              <strong title={name}>{name}</strong>
              <small>{message.attachmentSize ? formatSize(message.attachmentSize) : ""}</small>
            </div>
            <a className="link" href={url} download={name}>{t("common.download")}</a>
          </div>
        )}
      {message.text && <p className="file-message-caption">{message.text}</p>}
    </div>
  );
}
