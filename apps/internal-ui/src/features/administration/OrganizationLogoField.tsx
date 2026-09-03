import { useRef, useState } from "react";

import { DecisionDialog } from "../../shared/DecisionDialog";
import { Button } from "../../shared/ui-controls";

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
          ? <img src={logoUrl} alt={`Логотип ${name}`} />
          : <span>{name.trim().slice(0, 2).toUpperCase() || "CR"}</span>}
      </div>
      <div className="administration-logo-copy">
        <strong>Логотип</strong>
        <span>PNG, JPEG или WebP · до 2 МБ</span>
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
            >
              {logoUrl ? "Заменить" : "Загрузить"}
            </Button>
            {logoUrl && (
              <Button
                variant="danger-outline"
                disabled={saving}
                onClick={() => setConfirmingRemoval(true)}
              >
                Удалить
              </Button>
            )}
          </div>
        )}
      </div>
      <DecisionDialog
        open={confirmingRemoval}
        onClose={() => setConfirmingRemoval(false)}
        tone="danger"
        icon="trash"
        title="Удалить логотип?"
        description="Вместо него в меню снова будет показан знак Chatbolls."
        actions={(
          <>
            <Button variant="secondary" onClick={() => setConfirmingRemoval(false)}>
              Отмена
            </Button>
            <Button
              variant="danger-outline"
              disabled={saving}
              onClick={() => {
                setConfirmingRemoval(false);
                onRemove();
              }}
            >
              Удалить
            </Button>
          </>
        )}
      />
    </div>
  );
}
