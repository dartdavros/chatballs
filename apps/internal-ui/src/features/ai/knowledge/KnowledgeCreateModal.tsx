import { Modal } from "antd";
import { useState } from "react";

import { FormField } from "../../../shared/form-controls";
import { Button } from "../../../shared/ui-controls";
import { createKnowledgeItem } from "./model";

type KnowledgeCreateModalProps = {
  onClose: () => void;
  onCreated: (id: number) => void;
};

export function KnowledgeCreateModal({ onClose, onCreated }: KnowledgeCreateModalProps) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [content, setContent] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!title.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const { knowledge } = await createKnowledgeItem({
        title: title.trim(),
        description: description.trim(),
        content,
      });
      onCreated(knowledge.id);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось создать знание");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open title="Создать знание" onCancel={onClose} footer={null} destroyOnClose>
      <div className="integration-form">
        <FormField label="Заголовок" value={title} onChange={setTitle} placeholder="например, FoxRay — тарифы" />
        <FormField label="Краткое описание" value={description} onChange={setDescription} placeholder="о чём это знание — агент видит описание в каталоге" />
        <label className="knowledge-content-field">
          <span>Содержимое (Markdown)</span>
          <textarea value={content} rows={10} onChange={(event) => setContent(event.target.value)} placeholder="Текст знания. Можно ссылаться на вложения по имени файла." />
        </label>
        {error && <div className="integration-form-error">{error}</div>}
        <div className="integration-form-actions">
          <Button variant="secondary" onClick={onClose}>Отмена</Button>
          <Button variant="primary" disabled={!title.trim() || busy} onClick={submit}>
            {busy ? "Создание…" : "Создать"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
