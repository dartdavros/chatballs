import { useState } from "react";

import { FormField, TextAreaField } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import { t } from "../../i18n";

// Форма карточки контакта (имя, описание, телефон, компания, город) — одна
// для контекст-панели чата и для карточки в «Контактах». Раскладки две:
// `rail` — компактная колонка панели чата по её макету;
// `card` — поля общего стандарта форм в две колонки по ширине карточки.

export type ContactCardFields = { name: string; description: string; phone: string; company: string; city: string };

const FIELDS: Array<{ key: Exclude<keyof ContactCardFields, "description">; label: string }> = [
  { key: "name", label: t("common.name") },
  { key: "phone", label: t("common.phone") },
  { key: "company", label: t("common.company") },
  { key: "city", label: t("common.city") },
];

export function ContactEditForm({ initial, layout = "rail", onSubmit, onCancel }: { initial: ContactCardFields; layout?: "rail" | "card"; onSubmit: (fields: ContactCardFields) => Promise<void>; onCancel: () => void }) {
  const [form, setForm] = useState(initial);
  const [saving, setSaving] = useState(false);
  const [errorText, setErrorText] = useState("");
  const put = (key: keyof ContactCardFields, value: string) => setForm((prev) => ({ ...prev, [key]: value }));
  const set = (key: keyof ContactCardFields) => (event: { target: { value: string } }) => put(key, event.target.value);

  async function save() {
    if (!form.name.trim()) {
      setErrorText(t("conversations.name_cannot_empty"));
      return;
    }
    setSaving(true);
    setErrorText("");
    try {
      await onSubmit(form);
    } catch (error) {
      setErrorText(error instanceof Error ? error.message : t("common.could_not_save"));
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
          <TextAreaField label={t("common.description")} value={form.description} onChange={(value) => put("description", value)} />
        </div>
        {errorText && <p className="contact-edit-error" role="alert">{errorText}</p>}
        <div className="contact-edit-actions">
          <Button variant="secondary" disabled={saving} onClick={onCancel}>{t("common.cancel")}</Button>
          <Button variant="primary" type="submit" disabled={saving}>{saving ? t("common.saving") : t("common.save")}</Button>
        </div>
      </form>
    );
  }

  return (
    <form className="ctx-contact-edit" onSubmit={submit}>
      <input value={form.name} onChange={set("name")} placeholder={t("common.name")} aria-label={t("common.name")} autoFocus />
      <textarea value={form.description} onChange={set("description")} placeholder={t("common.description")} aria-label={t("common.description")} rows={2} />
      <input value={form.phone} onChange={set("phone")} placeholder={t("common.phone")} aria-label={t("common.phone")} />
      <input value={form.company} onChange={set("company")} placeholder={t("common.company")} aria-label={t("common.company")} />
      <input value={form.city} onChange={set("city")} placeholder={t("common.city")} aria-label={t("common.city")} />
      {errorText && <p className="ctx-error">{errorText}</p>}
      <div className="ctx-note-actions">
        <button type="button" onClick={onCancel} disabled={saving}>{t("common.cancel")}</button>
        <button type="submit" className="primary" disabled={saving}>{t("common.save")}</button>
      </div>
    </form>
  );
}
