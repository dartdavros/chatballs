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
import { t } from "../../i18n";

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
      return t("portals.check_portal_name_address");
    }
  }
  return t("portals.could_not_create_portal_try");
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
    <Modal open={open} title={t("portals.new_support_portal")} footer={null} onCancel={onClose}>
      <div className="portal-dialog-form">
        <p>{t("portals.portal_public_help_centre_with")}</p>
        <FormField error={fieldErrors.name} label={t("portals.portal_name")} value={name} onChange={setName} placeholder={t("portals.example_help_centre")} wide />
        <label className={`portal-address-field${fieldErrors.slug ? " is-invalid" : ""}`}>
          <span>{t("portals.portal_address")}</span>
          <div>
            <input
              type="text"
              value={slug}
              onChange={(event) => setSlug(event.target.value.toLocaleLowerCase())}
              placeholder="help"
              autoComplete="off"
              maxLength={63}
              pattern="[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
            />
            <b>.{address.baseDomain}</b>
          </div>
          <small>{t("portals.use_lowercase_latin_letters_digits")}</small>
          {fieldErrors.slug && <small className="form-field-error" role="alert">{fieldErrors.slug}</small>}
          {slug.trim() && <code>{configuredAddress(address, slug.trim())}</code>}
        </label>
        <SelectField
          label={t("portals.primary_language")}
          value={locale}
          onChange={setLocale}
          options={[["ru", t("portals.russian")], ["en", "English"]]}
        />
        {error && <div className="portal-form-error">{error}</div>}
        <div className="portal-dialog-actions">
          <Button variant="secondary" onClick={onClose}>{t("common.cancel")}</Button>
          <Button variant="primary" disabled={busy || !name.trim() || !portalKeyValid} onClick={() => void submit()}>
            {busy ? t("portals.creating") : t("portals.create_portal")}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
