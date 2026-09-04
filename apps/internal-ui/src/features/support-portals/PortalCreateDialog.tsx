import { Modal } from "antd";
import { useState } from "react";

import { ApiError } from "../../api/client";
import { FormField, SelectField } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import {
  createSupportPortal,
  portalFieldErrors,
  type PortalAddressConfig,
  type SupportPortal,
} from "./model";

function configuredAddress(config: PortalAddressConfig, slug: string): string {
  const port = config.port ? `:${config.port}` : "";
  return `${config.scheme}://${slug}.${config.baseDomain}${port}`;
}

function validPortalKey(value: string): boolean {
  return /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(value);
}

function creationError(caught: unknown): string {
  if (caught instanceof ApiError) {
    if (caught.status === 400) {
      return "Проверьте название и адрес портала.";
    }
  }
  return "Не удалось создать портал. Повторите попытку позже.";
}

export function PortalCreateDialog({
  open,
  onClose,
  onCreated,
  address,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (portal: SupportPortal) => void;
  address: PortalAddressConfig;
}) {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [locale, setLocale] = useState("ru");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const portalKeyValid = validPortalKey(slug.trim());

  async function submit() {
    setBusy(true);
    setError("");
    setFieldErrors({});
    try {
      const payload = await createSupportPortal({
        name,
        slug,
        defaultLocale: locale,
      });
      onCreated(payload.portal);
    } catch (caught) {
      setFieldErrors(portalFieldErrors(caught));
      setError(creationError(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open={open} title="Новый портал поддержки" footer={null} onCancel={onClose}>
      <div className="portal-dialog-form">
        <p>Портал — это публичный центр помощи с инструкциями и ответами для клиентов.</p>
        <FormField error={fieldErrors.name} label="Название портала" value={name} onChange={setName} placeholder="Например, Центр помощи Foxray" wide />
        <label className={`portal-address-field${fieldErrors.slug ? " is-invalid" : ""}`}>
          <span>Адрес Chatbolls</span>
          <div>
            <input
              type="text"
              value={slug}
              onChange={(event) => setSlug(event.target.value.toLocaleLowerCase())}
              placeholder="foxray"
              autoComplete="off"
              maxLength={63}
              pattern="[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
            />
            <b>.{address.baseDomain}</b>
          </div>
          <small>Используйте строчные латинские буквы, цифры и дефисы.</small>
          {fieldErrors.slug && <small className="form-field-error" role="alert">{fieldErrors.slug}</small>}
          {slug.trim() && <code>{configuredAddress(address, slug.trim())}</code>}
        </label>
        <SelectField
          label="Основной язык"
          value={locale}
          onChange={setLocale}
          options={[["ru", "Русский"], ["en", "English"]]}
        />
        {error && <div className="portal-form-error">{error}</div>}
        <div className="portal-dialog-actions">
          <Button variant="secondary" onClick={onClose}>Отмена</Button>
          <Button variant="primary" disabled={busy || !name.trim() || !portalKeyValid} onClick={() => void submit()}>
            {busy ? "Создаём…" : "Создать портал"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
