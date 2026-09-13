import { type FormEvent, useEffect, useMemo, useState } from "react";

import { ApiError } from "../../api/client";
import { OrganizationLogoField } from "../administration/OrganizationLogoField";
import { FormField, SelectField } from "../../shared/form-controls";
import { BackLink, Button } from "../../shared/ui-controls";
import { timezoneLabel } from "../../shared/utils";
import { t } from "../../i18n";
import type { AuthenticatedUser, SessionUser } from "../../types";
import {
  createOrganization,
  loadOrganizationCreateOptions,
  uploadNewOrganizationLogo,
  type OrganizationCreateOptions,
  type OrganizationDraft,
} from "./api";

// Страница создания организации (переключатель A1 → «Добавить организацию»).
// Те же поля, что в «Настройках → Организация»: имя, часовой пояс, валюта,
// язык, логотип. Создавший становится владельцем и сразу переключается в
// новую организацию — ответ сервера уже содержит обновлённый список членств.

type FieldErrors = Partial<Record<keyof OrganizationDraft, string>>;

export function OrganizationCreatePage({ user, onCreated, onBack }: {
  user: SessionUser;
  onCreated: (identity: AuthenticatedUser, organizationPublicId: string) => void;
  onBack: () => void;
}) {
  const [options, setOptions] = useState<OrganizationCreateOptions | null>(null);
  const [draft, setDraft] = useState<OrganizationDraft>({
    name: "",
    // Новая организация наследует региональные параметры текущей: чаще всего
    // человек заводит вторую компанию там же, где первую.
    timezone: "Europe/Moscow",
    currency: "RUB",
    language: "",
  });
  const [logo, setLogo] = useState<File | null>(null);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let active = true;
    loadOrganizationCreateOptions()
      .then((payload) => { if (active) setOptions(payload); })
      .catch((requestError) => {
        if (active) setError(requestError instanceof ApiError ? requestError.message : t("common.request_failed"));
      });
    return () => { active = false; };
  }, []);

  const logoPreview = useMemo(() => (logo ? URL.createObjectURL(logo) : null), [logo]);
  useEffect(() => () => { if (logoPreview) URL.revokeObjectURL(logoPreview); }, [logoPreview]);

  const valid = draft.name.trim() !== "" && !submitting;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!valid) return;
    setSubmitting(true);
    setError("");
    setErrors({});
    let created;
    try {
      created = await createOrganization(draft);
    } catch (requestError) {
      if (requestError instanceof ApiError) {
        const fieldErrors = (requestError.payload as { errors?: FieldErrors }).errors;
        if (fieldErrors) setErrors(fieldErrors);
        setError(requestError.message);
      } else {
        setError(t("organizations.create_failed"));
      }
      setSubmitting(false);
      return;
    }
    if (logo) {
      // Логотип — уже в созданную организацию. Его неудача организацию не
      // отменяет: человек попадает в неё и доложит логотип в «Настройках».
      try {
        await uploadNewOrganizationLogo(created.organizationPublicId, logo);
      } catch {
        window.setTimeout(() => window.alert(t("organizations.logo_failed")), 0);
      }
    }
    onCreated(created.user, created.organizationPublicId);
  }

  const timezones = options?.timezones ?? [draft.timezone];
  const languages = options?.languages ?? [];

  return (
    <div className="organization-create">
      <BackLink label={user.organizationName || "Chatballs"} onClick={onBack} />
      <header className="organization-create-head">
        <h2>{t("organizations.create_title")}</h2>
        <p>{t("organizations.create_lead")}</p>
      </header>
      <form className="administration-card administration-organization" onSubmit={submit}>
        <OrganizationLogoField
          logoUrl={logoPreview}
          name={draft.name}
          disabled={false}
          saving={submitting}
          onUpload={setLogo}
          onRemove={() => setLogo(null)}
        />
        <div className="administration-fields">
          <div className="administration-field-wide">
            <FormField
              label={t("admin.organization_name")}
              value={draft.name}
              placeholder={t("organizations.name_placeholder")}
              error={errors.name}
              onChange={(name) => setDraft({ ...draft, name })}
            />
          </div>
          <SelectField
            label={t("admin.time_zone")}
            value={draft.timezone}
            onChange={(timezone) => setDraft({ ...draft, timezone })}
            options={timezones.map((timezone) => [timezone, timezoneLabel(timezone)])}
          />
          <SelectField
            label={t("admin.currency")}
            value={draft.currency}
            onChange={(currency) => setDraft({ ...draft, currency })}
            options={[["RUB", t("admin.russian_rouble_rub")]]}
          />
        </div>
        <div className="appearance-row administration-language">
          <span>{t("settings.language")}</span>
          <div className="appearance-theme-options">
            <button
              className={draft.language === "" ? "active" : ""}
              type="button"
              onClick={() => setDraft({ ...draft, language: "" })}
            >
              {t("settings.language_as_installation")}
            </button>
            {languages.map((item) => (
              <button
                className={draft.language === item.code ? "active" : ""}
                key={item.code}
                lang={item.code}
                type="button"
                onClick={() => setDraft({ ...draft, language: item.code })}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
        <p className="settings-section-note">{t("settings.language_org_hint")}</p>
        {error && <div className="administration-message error" role="alert">{error}</div>}
        <div className="administration-actions">
          <Button variant="secondary" disabled={submitting} onClick={onBack}>{t("common.cancel")}</Button>
          <Button type="submit" variant="primary" icon="plus" disabled={!valid}>
            {submitting ? t("organizations.creating") : t("organizations.create_submit")}
          </Button>
        </div>
      </form>
    </div>
  );
}
