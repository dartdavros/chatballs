import { type FormEvent, useEffect, useState } from "react";

import { api } from "../../api/client";
import type { SessionUser } from "../../types";

type UserPayload = { authenticated: true; user: SessionUser };

export function useProfilePage({ user, onUserUpdated, reload }: { user: SessionUser; onUserUpdated: (user: SessionUser) => void; reload: () => void }) {
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

  return {
    profile,
    passwords,
    profileMessage,
    passwordMessage,
    totpMessage,
    sessionsMessage,
    savingProfile,
    savingPassword,
    savingTotp,
    revokingSessions,
    passwordMismatch,
    passwordReady,
    setProfile,
    setPasswords,
    saveProfile,
    updatePassword,
    toggleTotp,
    revokeOtherSessions,
  };
}
