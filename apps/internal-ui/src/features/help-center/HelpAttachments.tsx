import type { HelpAttachment } from "./types";
import { t } from "../../i18n";
import { readableSize } from "../../shared/utils";

// Вложения статьи портала: картинки вставлены в текст самой статьёй, а
// документы посетитель скачивает списком под ней — с иконкой формата и
// размером, чтобы было понятно, что открываешь.

const EXTENSION_LABEL: Record<string, string> = {
  pdf: "PDF",
  doc: "DOC",
  docx: "DOC",
  xls: "XLS",
  xlsx: "XLS",
  csv: "CSV",
  ppt: "PPT",
  pptx: "PPT",
  txt: "TXT",
  md: "MD",
  zip: "ZIP",
  rar: "ZIP",
  "7z": "ZIP",
  png: "PNG",
  jpg: "JPG",
  jpeg: "JPG",
  webp: "WEBP",
  gif: "GIF",
  svg: "SVG",
  avif: "AVIF",
  mp4: "MP4",
  mp3: "MP3",
};

function extensionOf(name: string): string {
  const parts = name.split(".");
  return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : "";
}

function formatLabel(name: string): string {
  const extension = extensionOf(name);
  return EXTENSION_LABEL[extension] ?? (extension ? extension.toUpperCase().slice(0, 4) : t("portals.file"));
}

export function HelpAttachments({ attachments }: { attachments: HelpAttachment[] }) {
  if (attachments.length === 0) return null;
  return (
    <section className="help-attachments">
      <h2>{t("portals.files_article_2")}</h2>
      <ul>
        {attachments.map((attachment) => (
          <li key={attachment.path}>
            <a download href={attachment.path}>
              <i data-format={formatLabel(attachment.name)}>{formatLabel(attachment.name)}</i>
              <span>
                <strong>{attachment.name}</strong>
                <small>{readableSize(attachment.size)}</small>
              </span>
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}
