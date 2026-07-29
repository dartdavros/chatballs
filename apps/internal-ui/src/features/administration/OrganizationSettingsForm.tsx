import type { FormEvent } from "react";

import { FormField, SelectField } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import type { OrganizationSettings } from "./model";
import { OrganizationLogoField } from "./OrganizationLogoField";

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
        <FormField
          label="Название организации"
          value={organization.name}
          disabled={!canManage}
          onChange={canManage
            ? (name) => onChange({ ...organization, name })
            : undefined}
        />
        <SelectField
          label="Часовой пояс"
          value={organization.timezone}
          disabled={!canManage}
          onChange={(timezone) => onChange({ ...organization, timezone })}
          options={timezones.map((timezone) => [timezone, timezone])}
        />
        <div className="administration-currency">
          <SelectField
            label="Валюта"
            value={organization.currency}
            disabled={!canManage}
            onChange={(currency) => onChange({ ...organization, currency })}
            options={[["RUB", "Российский рубль (RUB)"]]}
          />
        </div>
      </div>
      {error && <div className="administration-message error" role="alert">{error}</div>}
      {message && <div className="administration-message">{message}</div>}
      {canManage && (
        <div className="administration-actions">
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
