import { useRef } from "react";

import { Icon } from "../../../shared/icons";
import { Button } from "../../../shared/ui-controls";
import type { KnowledgeAttachment } from "./types";
import { formatSize } from "./model";

type AttachmentItem = KnowledgeAttachment | File;

function isUploaded(item: AttachmentItem): item is KnowledgeAttachment {
  return "url" in item;
}

export function KnowledgeAttachmentsCard({
  attachments,
  busy,
  onAdd,
  onDelete,
}: {
  attachments: AttachmentItem[];
  busy: boolean;
  onAdd: (files: File[]) => void;
  onDelete: (attachment: AttachmentItem) => void;
}) {
  const fileInput = useRef<HTMLInputElement>(null);

  return (
    <section className="knowledge-editor-card knowledge-attachments-card">
      <div className="knowledge-card-heading compact">
        <h3>Вложения</h3>
        <Button variant="secondary" icon="paperclip" disabled={busy} onClick={() => fileInput.current?.click()}>Загрузить файл</Button>
        <input
          hidden
          multiple
          ref={fileInput}
          type="file"
          onChange={(event) => {
            const files = [...(event.target.files ?? [])];
            event.target.value = "";
            if (files.length > 0) onAdd(files);
          }}
        />
      </div>
      <div className="knowledge-attachments">
        {attachments.map((attachment) => (
          <div className="knowledge-attachment-row" key={isUploaded(attachment) ? `uploaded-${attachment.id}` : `pending-${attachment.name}-${attachment.lastModified}`}>
            <Icon name="paperclip" size={15} />
            {isUploaded(attachment) ? <a href={attachment.url} target="_blank" rel="noreferrer">{attachment.name}</a> : <strong>{attachment.name}</strong>}
            <small>{formatSize(attachment.size)}{isUploaded(attachment) && attachment.hasText ? " · текст в поиске" : ""}</small>
            <button aria-label={`Удалить вложение ${attachment.name}`} disabled={busy} type="button" onClick={() => onDelete(attachment)}>
              <Icon name="trash" size={15} />
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}
