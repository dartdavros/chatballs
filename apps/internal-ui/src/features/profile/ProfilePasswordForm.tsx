import type { Dispatch, FormEvent, SetStateAction } from "react";

import { FormField } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import type { PasswordFormState } from "./types";
import { t } from "../../i18n";

// «Смена пароля» (дизайн-базлайн v2, кадр P1): три поля столбиком, кнопка
// справа внизу — вторичная, активна только когда форма заполнена.

export function ProfilePasswordForm({ passwords, message, mismatch, ready, saving, setPasswords, onSubmit }: { passwords: PasswordFormState; message: string; mismatch: boolean; ready: boolean; saving: boolean; setPasswords: Dispatch<SetStateAction<PasswordFormState>>; onSubmit: (event: FormEvent) => void }) {
  return (
    <form className="profile-card" onSubmit={onSubmit}>
      <h3>{t("profile.change_password")}</h3>
      <div className="password-fields">
        <FormField label={t("profile.current_password")} value={passwords.current} onChange={(value) => setPasswords((current) => ({ ...current, current: value }))} type="password" />
        <FormField label={t("common.new_password")} value={passwords.next} onChange={(value) => setPasswords((current) => ({ ...current, next: value }))} placeholder={t("profile.min_10_characters")} type="password" />
        <FormField label={t("common.repeat_new_password")} value={passwords.repeat} onChange={(value) => setPasswords((current) => ({ ...current, repeat: value }))} type="password" />
      </div>
      {mismatch && <div className="profile-message error">{t("common.passwords_do_not_match")}</div>}
      {message && <div className="profile-message">{message}</div>}
      <div className="profile-actions"><Button type="submit" variant="secondary" disabled={!ready || saving}>{saving ? t("profile.updating") : t("profile.update_password")}</Button></div>
    </form>
  );
}
