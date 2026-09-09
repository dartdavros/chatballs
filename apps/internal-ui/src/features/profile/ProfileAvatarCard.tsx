import { useRef, useState } from "react";

import { api, apiUpload } from "../../api/client";
import { DecisionDialog } from "../../shared/DecisionDialog";
import { Avatar } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import type { AuthenticatedUser, SessionUser } from "../../types";
import { t } from "../../i18n";

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
      setErrorText(error instanceof Error ? error.message : t("profile.could_not_upload_photo"));
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
      setErrorText(error instanceof Error ? error.message : t("profile.could_not_remove_photo"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="profile-card">
      <h3>{t("common.photo")}</h3>
      {errorText && <div className="profile-message">{errorText}</div>}
      <div className="administration-logo-field profile-avatar-field">
        <div className="profile-avatar-preview"><Avatar user={user} /></div>
        <div className="administration-logo-copy">
          <strong>{user.fullName || user.email}</strong>
          <span>{t("profile.png_jpeg_or_webp_up")}</span>
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
              {user.avatarUrl ? t("profile.replace") : t("common.upload")}
            </Button>
            {user.avatarUrl && (
              <Button variant="danger-outline" disabled={saving} onClick={() => setConfirmingRemoval(true)}>{t("common.delete")}</Button>
            )}
          </div>
        </div>
      </div>
      <DecisionDialog
        open={confirmingRemoval}
        onClose={() => setConfirmingRemoval(false)}
        tone="danger"
        icon="trash"
        title={t("profile.remove_photo")}
        description={t("profile.colleagues_will_see_initials_again")}
        actions={(
          <>
            <Button variant="secondary" onClick={() => setConfirmingRemoval(false)}>{t("common.cancel")}</Button>
            <Button variant="danger-outline" disabled={saving} onClick={() => { setConfirmingRemoval(false); void remove(); }}>{t("common.delete")}</Button>
          </>
        )}
      />
    </section>
  );
}
