import { useRef, useState } from "react";

import { api, apiUpload } from "../../api/client";
import { DecisionDialog } from "../../shared/DecisionDialog";
import { Avatar } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import type { AuthenticatedUser, SessionUser } from "../../types";

// Строка «Фото» внутри карточки «Личные данные» (дизайн-базлайн v2, кадр P1):
// круглое превью 56 · подпись · «Заменить» и «Удалить». Видно коллегам в чате,
// подписях сообщений и выборе ответственного.

export function ProfilePhotoField({ user, onUserUpdated }: { user: SessionUser; onUserUpdated: (user: SessionUser) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [saving, setSaving] = useState(false);
  const [errorText, setErrorText] = useState("");
  const [confirmingRemoval, setConfirmingRemoval] = useState(false);

  async function upload(file: File) {
    const form = new FormData();
    form.append("file", file);
    setSaving(true);
    setErrorText("");
    try {
      const payload = await apiUpload<{ user: AuthenticatedUser }>("/api/v1/auth/profile/avatar/", form);
      onUserUpdated({ ...user, ...payload.user });
    } catch (error) {
      setErrorText(error instanceof Error ? error.message : "Не удалось загрузить фото");
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    setSaving(true);
    setErrorText("");
    try {
      const payload = await api<{ user: AuthenticatedUser }>("/api/v1/auth/profile/avatar/", { method: "DELETE" });
      onUserUpdated({ ...user, ...payload.user });
    } catch (error) {
      setErrorText(error instanceof Error ? error.message : "Не удалось удалить фото");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="profile-photo-field">
      <span className="profile-photo-preview"><Avatar user={user} /></span>
      <div className="profile-photo-copy">
        <strong>Фото</strong>
        <small>PNG, JPEG или WebP · до 2 МБ. Видно коллегам в чате, подписях сообщений и выборе ответственного.</small>
        {errorText && <small className="profile-photo-error">{errorText}</small>}
      </div>
      <div className="profile-photo-actions">
        <input
          ref={input}
          type="file"
          accept="image/png,image/jpeg,image/webp"
          hidden
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) void upload(file);
            event.target.value = "";
          }}
        />
        <Button variant="secondary" disabled={saving} onClick={() => input.current?.click()}>Заменить</Button>
        <button className="profile-photo-remove" type="button" disabled={saving || !user.avatarUrl} onClick={() => setConfirmingRemoval(true)}>Удалить</button>
      </div>
      <DecisionDialog
        open={confirmingRemoval}
        onClose={() => setConfirmingRemoval(false)}
        tone="danger"
        icon="trash"
        title="Удалить фото?"
        description="Вместо фото коллеги снова увидят ваши инициалы."
        actions={(
          <>
            <Button variant="secondary" onClick={() => setConfirmingRemoval(false)}>Отмена</Button>
            <Button variant="danger-outline" disabled={saving} onClick={() => { setConfirmingRemoval(false); void remove(); }}>Удалить</Button>
          </>
        )}
      />
    </div>
  );
}
