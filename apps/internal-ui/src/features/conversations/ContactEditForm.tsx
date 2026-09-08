import { useState } from "react";

import { FormField, TextAreaField } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";

// Форма карточки контакта (имя, описание, телефон, компания, город) — одна
// для контекст-панели чата и для карточки в «Контактах». Раскладки две:
// `rail` — компактная колонка панели чата по её макету;
// `card` — поля общего стандарта форм в две колонки по ширине карточки.

export type ContactCardFields = { name: string; description: string; phone: string; company: string; city: string };

const FIELDS: Array<{ key: Exclude<keyof ContactCardFields, "description">; label: string }> = [
  { key: "name", label: "Имя" },
  { key: "phone", label: "Телефон" },
  { key: "company", label: "Компания" },
  { key: "city", label: "Город" },
];

export function ContactEditForm({ initial, layout = "rail", onSubmit, onCancel }: { initial: ContactCardFields; layout?: "rail" | "card"; onSubmit: (fields: ContactCardFields) => Promise<void>; onCancel: () => void }) {
  const [form, setForm] = useState(initial);
  const [saving, setSaving] = useState(false);
  const [errorText, setErrorText] = useState("");
  const put = (key: keyof ContactCardFields, value: string) => setForm((prev) => ({ ...prev, [key]: value }));
  const set = (key: keyof ContactCardFields) => (event: { target: { value: string } }) => put(key, event.target.value);

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

  function submit(event: { preventDefault: () => void }) {
    event.preventDefault();
    void save();
  }

  if (layout === "card") {
    return (
      <form className="contact-edit-card" onSubmit={submit}>
        <div className="contact-edit-grid">
          {FIELDS.map((field) => (
            <FormField key={field.key} label={field.label} value={form[field.key]} onChange={(value) => put(field.key, value)} />
          ))}
          <TextAreaField label="Описание" value={form.description} onChange={(value) => put("description", value)} />
        </div>
        {errorText && <p className="contact-edit-error" role="alert">{errorText}</p>}
        <div className="contact-edit-actions">
          <Button variant="secondary" disabled={saving} onClick={onCancel}>Отмена</Button>
          <Button variant="primary" type="submit" disabled={saving}>{saving ? "Сохранение" : "Сохранить"}</Button>
        </div>
      </form>
    );
  }

  return (
    <form className="ctx-contact-edit" onSubmit={submit}>
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
