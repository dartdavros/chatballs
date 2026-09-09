import type { FormEvent } from "react";

import { FormField, SelectField } from "../../shared/form-controls";
import { shortDateTime, timezoneLabel } from "../../shared/utils";
import { Button } from "../../shared/ui-controls";
import type { OrganizationLanguageOption } from "./api";
import type { OrganizationSettings } from "./model";
import { OrganizationLogoField } from "./OrganizationLogoField";
import { t } from "../../i18n";

function savedLabel(updatedAt: string | null): string {
  if (!updatedAt) return t("common.never_saved_yet");
  return t("time.saved_at", { time: shortDateTime(updatedAt) });
}

export function OrganizationSettingsForm({
  organization,
  canManage,
  saving,
  message,
  error,
  timezones,
  languages,
  onChange,
  onSave,
  onUploadLogo,
  onRemoveLogo,
}: {
  organization: OrganizationSettings;
  canManage: boolean;
  saving: boolean;
  message: string;
  error: string;
  timezones: string[];
  languages: OrganizationLanguageOption[];
  onChange: (next: OrganizationSettings) => void;
  onSave: () => void;
  onUploadLogo: (file: File) => void;
  onRemoveLogo: () => void;
}) {
  function submit(event: FormEvent) {
    event.preventDefault();
    onSave();
  }

  return (
    <form className="administration-card administration-organization" onSubmit={submit}>
      <OrganizationLogoField
        logoUrl={organization.logoUrl}
        name={organization.name}
        disabled={!canManage}
        saving={saving}
        onUpload={onUploadLogo}
        onRemove={onRemoveLogo}
      />
      <div className="administration-fields">
        <div className="administration-field-wide">
          <FormField
            label={t("admin.organization_name")}
            value={organization.name}
            disabled={!canManage}
            onChange={canManage
              ? (name) => onChange({ ...organization, name })
              : undefined}
          />
        </div>
        <SelectField
          label={t("admin.time_zone")}
          value={organization.timezone}
          disabled={!canManage}
          onChange={(timezone) => onChange({ ...organization, timezone })}
          options={timezones.map((timezone) => [timezone, timezoneLabel(timezone)])}
        />
        <SelectField
          label={t("settings.language")}
          value={organization.language}
          disabled={!canManage}
          onChange={(language) => onChange({ ...organization, language })}
          // Первый пункт — не язык, а отказ от выбора: организация без своего
          // языка следует за установкой, и владелец видит это словами.
          options={[
            ["", t("settings.language_as_installation")],
            ...languages.map((item): [string, string] => [item.code, item.label]),
          ]}
          hint={t("settings.language_org_hint")}
        />
        <SelectField
          label={t("admin.currency")}
          value={organization.currency}
          disabled={!canManage}
          onChange={(currency) => onChange({ ...organization, currency })}
          options={[["RUB", t("admin.russian_rouble_rub")]]}
        />
      </div>
      {error && <div className="administration-message error" role="alert">{error}</div>}
      {canManage && (
        <div className="administration-actions">
          {/* «Сохранено 2 сен, 14:12» — подпись у кнопки (кадр N1). */}
          <small className="administration-saved">{message || savedLabel(organization.updatedAt)}</small>
          <Button
            type="submit"
            variant="primary"
            disabled={saving || !organization.name.trim()}
          >
            {saving ? t("common.saving") : t("common.save")}
          </Button>
        </div>
      )}
    </form>
  );
}
