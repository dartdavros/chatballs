import { type FormEvent, useEffect, useState } from "react";

import { api } from "../../api/client";
import type { SessionUser } from "../../types";
import { Icon } from "../../shared/icons";
import { Avatar, RoleBadge } from "../../shared/ui";

type UserPayload = { authenticated: true; user: SessionUser };

export function ProfilePage({ user, onUserUpdated, reload, onLogout }: { user: SessionUser; onUserUpdated: (user: SessionUser) => void; reload: () => void; onLogout: () => void }) {
  const [profile, setProfile] = useState({ fullName: user.fullName || user.email, email: user.email });
  const [passwords, setPasswords] = useState({ current: "", next: "", repeat: "" });
  const [profileMessage, setProfileMessage] = useState("");
  const [passwordMessage, setPasswordMessage] = useState("");
  const [totpMessage, setTotpMessage] = useState("");
  const [sessionsMessage, setSessionsMessage] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);
  const [savingTotp, setSavingTotp] = useState(false);
  const [revokingSessions, setRevokingSessions] = useState(false);
  const passwordMismatch = passwords.repeat.length > 0 && passwords.next !== passwords.repeat;
  const passwordReady = passwords.current.length > 0 && passwords.next.length >= 10 && !passwordMismatch;

  useEffect(() => {
    setProfile({ fullName: user.fullName || user.email, email: user.email });
  }, [user.email, user.fullName]);

  async function saveProfile(event: FormEvent) {
    event.preventDefault();
    setSavingProfile(true);
    setProfileMessage("");
    try {
      const payload = await api<UserPayload>("/api/v1/auth/profile/update/", {
        method: "POST",
        body: JSON.stringify(profile),
      });
      onUserUpdated(payload.user);
      reload();
      setProfileMessage("Личные данные сохранены");
    } catch (error) {
      setProfileMessage(error instanceof Error ? error.message : "Не удалось сохранить профиль");
    } finally {
      setSavingProfile(false);
    }
  }

  async function updatePassword(event: FormEvent) {
    event.preventDefault();
    if (!passwordReady) return;
    setSavingPassword(true);
    setPasswordMessage("");
    try {
      const payload = await api<UserPayload & { revoked: number }>("/api/v1/auth/profile/password/", {
        method: "POST",
        body: JSON.stringify({ currentPassword: passwords.current, newPassword: passwords.next }),
      });
      onUserUpdated(payload.user);
      setPasswords({ current: "", next: "", repeat: "" });
      setPasswordMessage(payload.revoked > 0 ? `Пароль обновлён, завершено сессий: ${payload.revoked}` : "Пароль обновлён");
    } catch (error) {
      setPasswordMessage(error instanceof Error ? error.message : "Не удалось обновить пароль");
    } finally {
      setSavingPassword(false);
    }
  }

  async function toggleTotp() {
    setSavingTotp(true);
    setTotpMessage("");
    try {
      if (user.totpEnabled) {
        if (!passwords.current) {
          setTotpMessage("Введите текущий пароль в блоке смены пароля, чтобы отключить TOTP");
          return;
        }
        const payload = await api<UserPayload & { revoked: number }>("/api/v1/auth/profile/totp/disable/", {
          method: "POST",
          body: JSON.stringify({ currentPassword: passwords.current }),
        });
        onUserUpdated(payload.user);
        setTotpMessage(payload.revoked > 0 ? `TOTP отключена, завершено сессий: ${payload.revoked}` : "TOTP отключена");
      } else {
        const payload = await api<UserPayload>("/api/v1/auth/profile/totp/start/", { method: "POST" });
        onUserUpdated(payload.user);
      }
    } catch (error) {
      setTotpMessage(error instanceof Error ? error.message : "Не удалось изменить TOTP");
    } finally {
      setSavingTotp(false);
    }
  }

  async function revokeOtherSessions() {
    setRevokingSessions(true);
    setSessionsMessage("");
    try {
      const payload = await api<{ revoked: number }>("/api/v1/auth/profile/sessions/revoke-other/", { method: "POST" });
      setSessionsMessage(payload.revoked > 0 ? `Завершено сессий: ${payload.revoked}` : "Других активных сессий нет");
    } catch (error) {
      setSessionsMessage(error instanceof Error ? error.message : "Не удалось завершить сессии");
    } finally {
      setRevokingSessions(false);
    }
  }

  return (
    <div className="profile-stack">
      <section className="profile-header-card">
        <Avatar user={user} />
        <div className="profile-header-main">
          <div><h1>{profile.fullName || profile.email}</h1><RoleBadge role={user.role} /></div>
          <p>{profile.email}</p>
        </div>
        <button className="danger-outline" type="button" onClick={onLogout}><Icon name="logout" size={15} />Выйти</button>
      </section>

      <form className="profile-card" onSubmit={saveProfile}>
        <h3>Личные данные</h3>
        <div className="profile-grid">
          <ProfileField label="Имя" value={profile.fullName} onChange={(value) => setProfile((current) => ({ ...current, fullName: value }))} />
          <ProfileField label="Email · используется для входа" value={profile.email} onChange={(value) => setProfile((current) => ({ ...current, email: value }))} mono />
          <ProfileField label="Роль" value={user.role} disabled />
        </div>
        {profileMessage && <div className="profile-message">{profileMessage}</div>}
        <div className="profile-actions"><button className="primary-button" type="submit" disabled={savingProfile}>{savingProfile ? "Сохранение" : "Сохранить"}</button></div>
      </form>

      <form className="profile-card" onSubmit={updatePassword}>
        <h3>Смена пароля</h3>
        <div className="password-fields">
          <ProfileField label="Текущий пароль" value={passwords.current} onChange={(value) => setPasswords((current) => ({ ...current, current: value }))} type="password" />
          <ProfileField label="Новый пароль" value={passwords.next} onChange={(value) => setPasswords((current) => ({ ...current, next: value }))} placeholder="мин. 10 символов" type="password" />
          <ProfileField label="Повторите новый пароль" value={passwords.repeat} onChange={(value) => setPasswords((current) => ({ ...current, repeat: value }))} type="password" />
        </div>
        {passwordMismatch && <div className="profile-message error">Пароли не совпадают</div>}
        {passwordMessage && <div className="profile-message">{passwordMessage}</div>}
        <div className="profile-actions"><button className="secondary-button" type="submit" disabled={!passwordReady || savingPassword}>{savingPassword ? "Обновление" : "Обновить пароль"}</button></div>
      </form>

      <section className="profile-card totp-card">
        <div>
          <h3>Двухфакторная аутентификация (TOTP)</h3>
          <p>{user.totpEnabled ? "Включена. Для OWNER рекомендуется держать включённой." : "Отключена. Для роли OWNER настоятельно рекомендуется включить."}</p>
        </div>
        <button className={`totp-switch ${user.totpEnabled ? "on" : ""}`} type="button" role="switch" aria-checked={user.totpEnabled} onClick={toggleTotp} disabled={savingTotp}><i /></button>
        {totpMessage && <div className="security-note warning">{totpMessage}</div>}
        {user.totpEnabled && <div className="security-note ok">Приложение-аутентификатор подключено · последний код принят 5 мин назад</div>}
      </section>

      <section className="sessions-card">
        <div className="sessions-head"><h3>Активные сессии</h3><button type="button" onClick={revokeOtherSessions} disabled={revokingSessions}>{revokingSessions ? "Завершение" : "Завершить другие сессии"}</button></div>
        {sessionsMessage && <div className="profile-message sessions">{sessionsMessage}</div>}
        <div className="session-row"><span className="session-icon"><Icon name="user" /></span><span><strong>Браузер</strong><small>сейчас активна</small></span><b>текущая</b></div>
      </section>
    </div>
  );
}

function ProfileField({ label, value, onChange, placeholder = "", type = "text", mono = false, disabled = false }: { label: string; value: string; onChange?: (value: string) => void; placeholder?: string; type?: "text" | "password"; mono?: boolean; disabled?: boolean }) {
  return (
    <label className="readonly-field">
      <span>{label}</span>
      <input className={mono ? "mono" : ""} type={type} value={value} placeholder={placeholder} disabled={disabled} onChange={(event) => onChange?.(event.target.value)} />
    </label>
  );
}
