import type { Dispatch, FormEvent, SetStateAction } from "react";

import type { SessionUser } from "../../types";
import { FormField } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import { ProfilePhotoField } from "./ProfilePhotoField";
import type { ProfileFormState } from "./types";
import { t } from "../../i18n";

// «Личные данные» (дизайн-базлайн v2, кадр P1): фото отдельной строкой сверху,
// затем имя и email в две колонки. Поля «Роль» здесь нет — роль показана
// бейджем в шапке страницы.

export function ProfileInfoForm({ profile, user, message, saving, setProfile, onUserUpdated, onSubmit }: {
  profile: ProfileFormState;
  user: SessionUser;
  message: string;
  saving: boolean;
  setProfile: Dispatch<SetStateAction<ProfileFormState>>;
  onUserUpdated: (user: SessionUser) => void;
  onSubmit: (event: FormEvent) => void;
}) {
  return (
    <form className="profile-card" onSubmit={onSubmit}>
      <h3>{t("profile.personal_details")}</h3>
      <ProfilePhotoField user={user} onUserUpdated={onUserUpdated} />
      <div className="profile-grid">
        <FormField label={t("common.name")} value={profile.fullName} onChange={(value) => setProfile((current) => ({ ...current, fullName: value }))} />
        <FormField label={t("profile.email_used_sign")} value={profile.email} onChange={(value) => setProfile((current) => ({ ...current, email: value }))} mono />
      </div>
      {message && <div className="profile-message">{message}</div>}
      <div className="profile-actions"><Button type="submit" variant="primary" disabled={saving}>{saving ? t("common.saving") : t("common.save")}</Button></div>
    </form>
  );
}
