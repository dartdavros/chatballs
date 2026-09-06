import type { Dispatch, FormEvent, SetStateAction } from "react";

import { FormField } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import type { PasswordFormState } from "./types";

// «Смена пароля» (дизайн-базлайн v2, кадр P1): три поля столбиком, кнопка
// справа внизу — вторичная, активна только когда форма заполнена.

export function ProfilePasswordForm({ passwords, message, mismatch, ready, saving, setPasswords, onSubmit }: { passwords: PasswordFormState; message: string; mismatch: boolean; ready: boolean; saving: boolean; setPasswords: Dispatch<SetStateAction<PasswordFormState>>; onSubmit: (event: FormEvent) => void }) {
  return (
    <form className="profile-card" onSubmit={onSubmit}>
      <h3>Смена пароля</h3>
      <div className="password-fields">
        <FormField label="Текущий пароль" value={passwords.current} onChange={(value) => setPasswords((current) => ({ ...current, current: value }))} type="password" />
        <FormField label="Новый пароль" value={passwords.next} onChange={(value) => setPasswords((current) => ({ ...current, next: value }))} placeholder="мин. 10 символов" type="password" />
        <FormField label="Повторите новый пароль" value={passwords.repeat} onChange={(value) => setPasswords((current) => ({ ...current, repeat: value }))} type="password" />
      </div>
      {mismatch && <div className="profile-message error">Пароли не совпадают</div>}
      {message && <div className="profile-message">{message}</div>}
      <div className="profile-actions"><Button type="submit" variant="secondary" disabled={!ready || saving}>{saving ? "Обновление" : "Обновить пароль"}</Button></div>
    </form>
  );
}
