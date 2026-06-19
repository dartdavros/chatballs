import type { Dispatch, FormEvent, SetStateAction } from "react";

import type { SessionUser } from "../../types";
import { Button } from "../../shared/ui-controls";
import { ProfileField } from "./ProfileField";
import type { ProfileFormState } from "./types";

export function ProfileInfoForm({ profile, user, message, saving, setProfile, onSubmit }: { profile: ProfileFormState; user: SessionUser; message: string; saving: boolean; setProfile: Dispatch<SetStateAction<ProfileFormState>>; onSubmit: (event: FormEvent) => void }) {
  return (
    <form className="profile-card" onSubmit={onSubmit}>
      <h3>Личные данные</h3>
      <div className="profile-grid">
        <ProfileField label="Имя" value={profile.fullName} onChange={(value) => setProfile((current) => ({ ...current, fullName: value }))} />
        <ProfileField label="Email · используется для входа" value={profile.email} onChange={(value) => setProfile((current) => ({ ...current, email: value }))} mono />
        <ProfileField label="Роль" value={user.role} disabled />
      </div>
      {message && <div className="profile-message">{message}</div>}
      <div className="profile-actions"><Button type="submit" variant="primary" disabled={saving}>{saving ? "Сохранение" : "Сохранить"}</Button></div>
    </form>
  );
}
