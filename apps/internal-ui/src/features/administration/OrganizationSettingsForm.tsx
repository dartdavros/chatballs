import type { FormEvent } from "react";

import { FormField, SelectField } from "../../shared/form-controls";
import { shortDateTime, timezoneLabel } from "../../shared/utils";
import { Button } from "../../shared/ui-controls";
import type { OrganizationSettings } from "./model";
import { OrganizationLogoField } from "./OrganizationLogoField";

function savedLabel(updatedAt: string | null): string {
  if (!updatedAt) return "Ещё не сохранялось";
  return `Сохранено ${shortDateTime(updatedAt)}`;
}

export function OrganizationSettingsForm({
  organization,
  canManage,
  saving,
  message,
  error,
  timezones,
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
            label="Название организации"
            value={organization.name}
            disabled={!canManage}
            onChange={canManage
              ? (name) => onChange({ ...organization, name })
              : undefined}
          />
        </div>
        <SelectField
          label="Часовой пояс"
          value={organization.timezone}
          disabled={!canManage}
          onChange={(timezone) => onChange({ ...organization, timezone })}
          options={timezones.map((timezone) => [timezone, timezoneLabel(timezone)])}
        />
        <SelectField
          label="Валюта"
          value={organization.currency}
          disabled={!canManage}
          onChange={(currency) => onChange({ ...organization, currency })}
          options={[["RUB", "Российский рубль (RUB)"]]}
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
            {saving ? "Сохранение" : "Сохранить"}
          </Button>
        </div>
      )}
    </form>
  );
}
