import { Modal } from "antd";
import { useState } from "react";

import { api } from "../../../api/client";
import { FormField } from "../../../shared/form-controls";
import { Button } from "../../../shared/ui-controls";
import type { ChannelRef } from "../model";

export function ChannelEditForm({ channel, onClose, onSaved }: { channel: ChannelRef; onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState(channel.name);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ready = name.trim().length > 0;

  async function submit() {
    if (!ready) return;
    setSubmitting(true);
    setError(null);
    try {
      await api(`/api/v1/channels/${channel.id}/`, { method: "PATCH", body: JSON.stringify({ name: name.trim() }) });
      onSaved();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось сохранить");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open title="Изменить канал" onCancel={onClose} footer={null} destroyOnClose>
      <div className="integration-form">
        <FormField label="Название канала" value={name} onChange={setName} placeholder="название канала" />
        {error && <div className="integration-form-error">{error}</div>}
        <div className="integration-form-actions">
          <Button variant="secondary" onClick={onClose}>Отмена</Button>
          <Button variant="primary" disabled={!ready || submitting} onClick={submit}>{submitting ? "Сохранение…" : "Сохранить"}</Button>
        </div>
      </div>
    </Modal>
  );
}
