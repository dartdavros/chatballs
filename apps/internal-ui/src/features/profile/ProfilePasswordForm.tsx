import type { Dispatch, FormEvent, SetStateAction } from "react";

import { ProfileField } from "./ProfileField";
import type { PasswordFormState } from "./types";

export function ProfilePasswordForm({ passwords, message, mismatch, ready, saving, setPasswords, onSubmit }: { passwords: PasswordFormState; message: string; mismatch: boolean; ready: boolean; saving: boolean; setPasswords: Dispatch<SetStateAction<PasswordFormState>>; onSubmit: (event: FormEvent) => void }) {
  return (
    <form className="profile-card" onSubmit={onSubmit}>
      <h3>Смена пароля</h3>
      <div className="password-fields">
        <ProfileField label="Текущий пароль" value={passwords.current} onChange={(value) => setPasswords((current) => ({ ...current, current: value }))} type="password" />
        <ProfileField label="Новый пароль" value={passwords.next} onChange={(value) => setPasswords((current) => ({ ...current, next: value }))} placeholder="мин. 10 символов" type="password" />
        <ProfileField label="Повторите новый пароль" value={passwords.repeat} onChange={(value) => setPasswords((current) => ({ ...current, repeat: value }))} type="password" />
      </div>
      {mismatch && <div className="profile-message error">Пароли не совпадают</div>}
      {message && <div className="profile-message">{message}</div>}
      <div className="profile-actions"><button className="secondary-button" type="submit" disabled={!ready || saving}>{saving ? "Обновление" : "Обновить пароль"}</button></div>
    </form>
  );
}
