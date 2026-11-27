import { Icon } from "../../shared/icons";
import { fileMarkdown, fileMeta, isImageFile } from "../../shared/markdown/markdownTools";
import { t } from "../../i18n";
import type { PortalArticleEditorState } from "./usePortalArticleEditor";

export function PortalArticleFiles({ state, canManage }: {
  state: PortalArticleEditorState;
  canManage: boolean;
}) {
  const { fileInputRef, imageInputRef, upload, railDropping, setRailDropping,
    uploading, files, content, insertText, removeFile } = state;
  return (
    <div className="portal-rail-block">
      <div className="portal-rail-head">
        <span>{t("portals.article_files")}</span>
        <button type="button" onClick={() => fileInputRef.current?.click()}>{t("common.upload")}</button>
      </div>
      {/* Два механизма и два поля выбора: скрепка и рейка прикрепляют
          файл к статье, кнопка «изображение» ставит картинку в текст. */}
      <input
        ref={fileInputRef}
        hidden
        multiple
        type="file"
        onChange={(event) => {
          if (event.target.files?.length) void upload(event.target.files, false);
          event.target.value = "";
        }}
      />
      <input
        ref={imageInputRef}
        hidden
        multiple
        accept="image/*"
        type="file"
        onChange={(event) => {
          if (event.target.files?.length) void upload(event.target.files, true);
          event.target.value = "";
        }}
      />
      <div
        className={`portal-rail-drop${railDropping ? " is-hot" : ""}`}
        onDragEnter={(event) => { event.preventDefault(); setRailDropping(true); }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={() => setRailDropping(false)}
        onDrop={(event) => {
          event.preventDefault();
          setRailDropping(false);
          if (event.dataTransfer.files.length) void upload(event.dataTransfer.files, false);
        }}
      >
        <Icon name="upload" size={20} strokeWidth={1.8} />
        <p>{t("ai.drag_files_here")}</p>
        <p>{t("ai.or")}<button type="button" onClick={() => fileInputRef.current?.click()}>{t("ai.pick_them_from_disk")}</button>{t("ai.up_25_mb")}</p>
      </div>

      <div className="portal-rail-files">
        {uploading && (
          <div className="portal-rail-file is-fresh">
            <i><Icon name="image" size={14} strokeWidth={1.8} /></i>
            <span>
              <strong>{uploading.name}</strong>
              <small className="is-progress">{t("common.uploading_percent", { percent: uploading.percent })}</small>
              <span className="portal-rail-progress"><i style={{ width: `${uploading.percent}%` }} /></span>
            </span>
          </div>
        )}
        {files.map((file) => {
          const image = isImageFile(file.contentType, file.name);
          const inserted = content.includes(file.path) || content.includes(file.url);
          return (
            <div className="portal-rail-file" key={file.id}>
              <i><Icon name={image ? "image" : "file"} size={14} strokeWidth={1.8} /></i>
              <span>
                <strong>{file.name}</strong>
                <small>{fileMeta(file.name, file.size)}{inserted ? ` ${t("portals.inserted_into_text")}` : ` ${t("portals.article_attachment")}`}</small>
              </span>
              {/* В текст вставляется только картинка: документ — вложение
                  статьи, посетитель скачивает его списком под текстом. */}
              {image && !inserted && (
                <button
                  className="portal-rail-file-insert"
                  title={t("portals.insert_into_text")}
                  type="button"
                  onClick={() => insertText(`\n${fileMarkdown(file.name, file.path, true)}\n`)}
                >
                  <Icon name="plus" size={14} strokeWidth={2} />
                </button>
              )}
              <button
                title={t("ai.copy_as_markdown")}
                type="button"
                onClick={() => void navigator.clipboard?.writeText(fileMarkdown(file.name, file.path, image))}
              >
                <Icon name="copy" size={13} strokeWidth={1.9} />
              </button>
              {canManage && (
                <button className="portal-rail-file-remove" title={t("portals.delete_file")} type="button" onClick={() => void removeFile(file)}>
                  <Icon name="trash" size={13} strokeWidth={1.9} />
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
