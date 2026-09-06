import { useState } from "react";

// Форма карточки контакта (имя, описание, телефон, компания, город) — одна
// для контекст-панели чата и для карточки в «Контактах».

export type ContactCardFields = { name: string; description: string; phone: string; company: string; city: string };

export function ContactEditForm({ initial, onSubmit, onCancel }: { initial: ContactCardFields; onSubmit: (fields: ContactCardFields) => Promise<void>; onCancel: () => void }) {
  const [form, setForm] = useState(initial);
  const [saving, setSaving] = useState(false);
  const [errorText, setErrorText] = useState("");
  const set = (key: keyof ContactCardFields) => (event: { target: { value: string } }) => setForm((prev) => ({ ...prev, [key]: event.target.value }));

  async function save() {
    if (!form.name.trim()) {
      setErrorText("Имя не может быть пустым");
      return;
    }
    setSaving(true);
    setErrorText("");
    try {
      await onSubmit(form);
    } catch (error) {
      setErrorText(error instanceof Error ? error.message : "Не удалось сохранить");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="ctx-contact-edit" onSubmit={(event) => { event.preventDefault(); void save(); }}>
      <input value={form.name} onChange={set("name")} placeholder="Имя" aria-label="Имя" autoFocus />
      <textarea value={form.description} onChange={set("description")} placeholder="Описание" aria-label="Описание" rows={2} />
      <input value={form.phone} onChange={set("phone")} placeholder="Телефон" aria-label="Телефон" />
      <input value={form.company} onChange={set("company")} placeholder="Компания" aria-label="Компания" />
      <input value={form.city} onChange={set("city")} placeholder="Город" aria-label="Город" />
      {errorText && <p className="ctx-error">{errorText}</p>}
      <div className="ctx-note-actions">
        <button type="button" onClick={onCancel} disabled={saving}>Отмена</button>
        <button type="submit" className="primary" disabled={saving}>Сохранить</button>
      </div>
    </form>
  );
}
