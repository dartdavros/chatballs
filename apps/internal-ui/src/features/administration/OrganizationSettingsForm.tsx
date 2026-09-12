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
          label={t("admin.currency")}
          value={organization.currency}
          disabled={!canManage}
          onChange={(currency) => onChange({ ...organization, currency })}
          options={[["RUB", t("admin.russian_rouble_rub")]]}
        />
      </div>
      {/* Язык — сегментом, как «Тема» в профиле и схема в «Платформе»: вариантов
          три, и выбор лучше видеть целиком, чем разворачивать список. В сетку
          полей он не встаёт — она выравнивает поля по нижнему краю, и строка с
          подписью ломала бы ряд. */}
      <div className="appearance-row administration-language">
        <span>{t("settings.language")}</span>
        <div className="appearance-theme-options">
          <button
            className={organization.language === "" ? "active" : ""}
            disabled={!canManage}
            type="button"
            onClick={() => onChange({ ...organization, language: "" })}
          >
            {t("settings.language_as_installation")}
          </button>
          {languages.map((item) => (
            <button
              className={organization.language === item.code ? "active" : ""}
              disabled={!canManage}
              key={item.code}
              lang={item.code}
              type="button"
              onClick={() => onChange({ ...organization, language: item.code })}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>
      <p className="settings-section-note">{t("settings.language_org_hint")}</p>
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
