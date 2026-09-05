import { useRef, useState } from "react";

import { api, apiUpload } from "../../api/client";
import { DecisionDialog } from "../../shared/DecisionDialog";
import { Avatar } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import type { AuthenticatedUser, SessionUser } from "../../types";

// Фото профиля (дизайн-базлайн v2): видно коллегам в сайдбаре, подписях
// сообщений и выборе ответственного. Тот же стандарт поля, что у логотипа
// организации: превью · «Заменить/Загрузить» · «Удалить» с подтверждением.

export function ProfileAvatarCard({ user, onUserUpdated }: { user: SessionUser; onUserUpdated: (user: SessionUser) => void }) {
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
    <section className="profile-card">
      <h3>Фото</h3>
      {errorText && <div className="profile-message">{errorText}</div>}
      <div className="administration-logo-field profile-avatar-field">
        <div className="profile-avatar-preview"><Avatar user={user} /></div>
        <div className="administration-logo-copy">
          <strong>{user.fullName || user.email}</strong>
          <span>PNG, JPEG или WebP · до 2 МБ. Видно коллегам в чате.</span>
          <div className="administration-logo-actions">
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
            <Button variant="secondary" disabled={saving} onClick={() => input.current?.click()}>
              {user.avatarUrl ? "Заменить" : "Загрузить"}
            </Button>
            {user.avatarUrl && (
              <Button variant="danger-outline" disabled={saving} onClick={() => setConfirmingRemoval(true)}>
                Удалить
              </Button>
            )}
          </div>
        </div>
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
    </section>
  );
}
