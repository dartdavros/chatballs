import { useRef, useState } from "react";

import { DecisionDialog } from "../../shared/DecisionDialog";
import { Button } from "../../shared/ui-controls";
import { t } from "../../i18n";

export function OrganizationLogoField({
  logoUrl,
  name,
  disabled,
  saving,
  onUpload,
  onRemove,
}: {
  logoUrl: string | null;
  name: string;
  disabled: boolean;
  saving: boolean;
  onUpload: (file: File) => void;
  onRemove: () => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [confirmingRemoval, setConfirmingRemoval] = useState(false);

  return (
    <div className="administration-logo-field">
      <div className="administration-logo-preview">
        {logoUrl
          ? <img src={logoUrl} alt={t("admin.organization_logo_alt", { name })} />
          : <span>{name.trim().slice(0, 2).toUpperCase() || "CR"}</span>}
      </div>
      <div className="administration-logo-copy">
        <strong>{t("admin.logo")}</strong>
        <span>{t("admin.png_jpeg_or_webp_up")}</span>
      </div>
      {!disabled && (
        <div className="administration-logo-actions">
          <input
            ref={input}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            hidden
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) onUpload(file);
              event.target.value = "";
            }}
          />
          <Button
            variant="secondary"
            disabled={saving}
            onClick={() => input.current?.click()}
          >{t("common.upload")}</Button>
          <button
            className="administration-logo-remove"
            type="button"
            disabled={saving || !logoUrl}
            onClick={() => setConfirmingRemoval(true)}
          >{t("common.remove")}</button>
        </div>
      )}
      <DecisionDialog
        open={confirmingRemoval}
        onClose={() => setConfirmingRemoval(false)}
        tone="danger"
        icon="trash"
        title={t("admin.remove_logo")}
        description={t("admin.chatballs_mark_will_shown_menu")}
        actions={(
          <>
            <Button variant="secondary" onClick={() => setConfirmingRemoval(false)}>{t("common.cancel")}</Button>
            <Button
              variant="danger-outline"
              disabled={saving}
              onClick={() => {
                setConfirmingRemoval(false);
                onRemove();
              }}
            >{t("common.delete")}</Button>
          </>
        )}
      />
    </div>
  );
}
