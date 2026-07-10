import { Modal } from "antd";
import { useEffect, useRef, useState } from "react";

import { Icon } from "../../../shared/icons";
import { FormField } from "../../../shared/form-controls";
import { EmptyState, LoadingState, StatusPill } from "../../../shared/ui";
import { Button } from "../../../shared/ui-controls";
import { formatDate } from "../../../shared/utils";
import type { RouteKey } from "../../../types";
import {
  deleteAttachment,
  deleteKnowledgeItem,
  fetchKnowledgeItem,
  formatSize,
  updateKnowledgeItem,
  uploadAttachment,
  type KnowledgeItem,
} from "./model";

export function KnowledgeDetailPage({ knowledgeId, setRoute, onLoaded }: { knowledgeId: number | null; setRoute: (route: RouteKey) => void; onLoaded: (title: string | null) => void }) {
  const [item, setItem] = useState<KnowledgeItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [content, setContent] = useState("");
  const [busy, setBusy] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  async function load() {
    if (!knowledgeId) {
      setError(true);
      setLoading(false);
      return;
    }
    try {
      const { knowledge } = await fetchKnowledgeItem(knowledgeId);
      setItem(knowledge);
      setTitle(knowledge.title);
      setDescription(knowledge.description);
      setContent(knowledge.content ?? "");
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [knowledgeId]);

  useEffect(() => {
    onLoaded(item?.title ?? null);
    return () => onLoaded(null);
  }, [item, onLoaded]);

  if (loading) return <div className="ai-page"><LoadingState /></div>;
  if (error || !item) return <div className="ai-page"><EmptyState title="Не удалось загрузить знание" /></div>;

  const dirty = title !== item.title || description !== item.description || content !== (item.content ?? "");

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setSaveError(null);
    try {
      await action();
      await load();
    } catch (caught) {
      setSaveError(caught instanceof Error ? caught.message : "Не удалось сохранить");
    } finally {
      setBusy(false);
    }
  }

  async function onUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !knowledgeId) return;
    await run(() => uploadAttachment(knowledgeId, file));
  }

  return (
    <div className="ai-page knowledge-detail">
      <section className="ai-card">
        <div className="knowledge-detail-head">
          <h3>Знание</h3>
          <div className="knowledge-detail-status">
            <StatusPill status={item.isEnabled ? "active" : "disabled"} />
            <span className="ai-doc-updated">обновлено {formatDate(item.updatedAt)}</span>
          </div>
        </div>
        <div className="knowledge-detail-fields">
          <FormField label="Заголовок" value={title} onChange={setTitle} />
          <FormField label="Краткое описание" value={description} onChange={setDescription} placeholder="о чём это знание — агент видит описание в каталоге" />
          <label className="knowledge-content-field">
            <span>Содержимое (Markdown)</span>
            <textarea value={content} rows={16} onChange={(event) => setContent(event.target.value)} placeholder="Текст знания. Можно ссылаться на вложения по имени файла." />
          </label>
        </div>
        {saveError && <div className="ai-doc-error">{saveError}</div>}
        <div className="ai-doc-actions">
          <Button variant="primary" icon="save" disabled={!dirty || !title.trim() || busy} onClick={() => run(() => updateKnowledgeItem(item.id, { title: title.trim(), description: description.trim(), content }))}>
            Сохранить
          </Button>
          <Button variant="secondary" icon={item.isEnabled ? "eyeOff" : "eye"} disabled={busy} onClick={() => run(() => updateKnowledgeItem(item.id, { isEnabled: !item.isEnabled }))}>
            {item.isEnabled ? "Выключить" : "Включить"}
          </Button>
          <Button variant="secondary" icon="trash" disabled={busy} onClick={() => setDeleteOpen(true)}>Удалить</Button>
        </div>
      </section>

      <section className="ai-card">
        <div className="knowledge-detail-head">
          <h3>Вложения</h3>
          <Button variant="secondary" icon="paperclip" disabled={busy} onClick={() => fileInput.current?.click()}>Загрузить файл</Button>
          <input ref={fileInput} type="file" hidden onChange={(event) => void onUpload(event)} />
        </div>
        <p className="knowledge-attachments-hint">
          Оригинальное имя файла сохраняется — ссылайтесь на него в тексте знания. Текст из md, txt, pdf и docx попадает в поиск знаний.
          По публичной ссылке агент может отправить файл клиенту.
        </p>
        {item.attachments.length === 0 ? (
          <EmptyState title="Вложений нет" />
        ) : (
          <ul className="knowledge-attachments">
            {item.attachments.map((attachment) => (
              <li key={attachment.id}>
                <Icon name="paperclip" size={15} />
                <a href={attachment.url} target="_blank" rel="noreferrer">{attachment.name}</a>
                <small>{formatSize(attachment.size)}{attachment.hasText ? " · текст в поиске" : ""}</small>
                <button type="button" className="row-menu-button" aria-label="Удалить вложение" disabled={busy} onClick={() => run(() => deleteAttachment(item.id, attachment.id))}>
                  <Icon name="trash" size={15} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {deleteOpen && (
        <Modal open title="Удалить знание?" onCancel={() => setDeleteOpen(false)} footer={null} destroyOnClose>
          <div className="integration-form">
            <p>Знание «{item.title}» и его вложения будут удалены. У агентов, использующих это знание, оно исчезнет из выбора.</p>
            <div className="integration-form-actions">
              <Button variant="secondary" onClick={() => setDeleteOpen(false)}>Отмена</Button>
              <Button variant="primary" disabled={busy} onClick={() => { setBusy(true); void deleteKnowledgeItem(item.id).then(() => setRoute("aiKnowledge")).catch(() => setBusy(false)); }}>Удалить</Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
