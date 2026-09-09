import { useEffect, useState } from "react";

import { api } from "../../api/client";
import { Icon } from "../../shared/icons";
import { useMediaQuery } from "../../shared/useMediaQuery";
import type { SessionUser } from "../../types";
import { fetchProfileSessions } from "./model";
import { ProfileAppearanceCard } from "./ProfileAppearanceCard";
import { ProfileHeader } from "./ProfileHeader";
import { ProfileInfoForm } from "./ProfileInfoForm";
import { ProfileLanguageCard } from "./ProfileLanguageCard";
import { ProfileNotificationsCard } from "./ProfileNotificationsCard";
import { ProfilePasswordForm } from "./ProfilePasswordForm";
import { ProfileSessionsCard } from "./ProfileSessionsCard";
import { ProfileTotpCard } from "./ProfileTotpCard";
import { useProfilePage } from "./useProfilePage";
import { t } from "../../i18n";

// «Профиль» — отдельная страница из меню пользователя (дизайн-базлайн v2,
// кадры P1/P2): слева «кто я и как выглядит интерфейс», справа безопасность.
// Всё здесь принадлежит учётной записи, а не организации (ADR-0029).

type MobileSection = "notifications" | "password" | "totp" | "sessions";

const MOBILE_TITLE: Record<MobileSection, string> = {
  notifications: t("profile.messenger_notifications"),
  password: t("profile.change_password"),
  totp: t("profile.two_factor_authentication"),
  sessions: t("common.active_sessions"),
};

export function ProfilePage({ user, onUserUpdated, reload, onLogout, onBack }: { user: SessionUser; onUserUpdated: (user: SessionUser) => void; reload: () => void; onLogout: () => void; onBack: () => void }) {
  const page = useProfilePage({ user, onUserUpdated, reload });
  // Кадр M: безопасность и уведомления уходят в подэкраны.
  const mobile = useMediaQuery("(max-width: 900px)");
  const [section, setSection] = useState<MobileSection | null>(null);
  const summary = useProfileSummary(mobile);

  const security = (
    <>
      <ProfilePasswordForm passwords={page.passwords} message={page.passwordMessage} mismatch={page.passwordMismatch} ready={page.passwordReady} saving={page.savingPassword} setPasswords={page.setPasswords} onSubmit={page.updatePassword} />
      <ProfileTotpCard user={user} message={page.totpMessage} saving={page.savingTotp} onToggle={page.toggleTotp} />
      <ProfileSessionsCard message={page.sessionsMessage} revoking={page.revokingSessions} onRevoke={page.revokeOtherSessions} />
    </>
  );

  if (mobile) {
    return (
      <div className="profile-page is-mobile">
        <div className="profile-mobile-bar">
          <button type="button" aria-label={t("profile.back")} onClick={() => (section ? setSection(null) : onBack())}><Icon name="chevronLeft" size={20} strokeWidth={2} /></button>
          <h2>{section ? MOBILE_TITLE[section] : t("common.profile")}</h2>
          {!section && <button className="profile-mobile-logout" type="button" onClick={onLogout}>{t("common.sign_out")}</button>}
        </div>
        <div className="profile-mobile-body">
          {section === "notifications" && <ProfileNotificationsCard />}
          {section === "password" && <ProfilePasswordForm passwords={page.passwords} message={page.passwordMessage} mismatch={page.passwordMismatch} ready={page.passwordReady} saving={page.savingPassword} setPasswords={page.setPasswords} onSubmit={page.updatePassword} />}
          {section === "totp" && <ProfileTotpCard user={user} message={page.totpMessage} saving={page.savingTotp} onToggle={page.toggleTotp} />}
          {section === "sessions" && <ProfileSessionsCard message={page.sessionsMessage} revoking={page.revokingSessions} onRevoke={page.revokeOtherSessions} />}
          {!section && (
            <>
              <ProfileHeader user={user} compact onLogout={onLogout} />
              <ProfileInfoForm profile={page.profile} user={user} message={page.profileMessage} saving={page.savingProfile} setProfile={page.setProfile} onUserUpdated={onUserUpdated} onSubmit={page.saveProfile} />
              <ProfileAppearanceCard user={user} onUserUpdated={onUserUpdated} />
              <ProfileLanguageCard user={user} onUserUpdated={onUserUpdated} />
              <div className="profile-mobile-list">
                <MobileLink label={MOBILE_TITLE.notifications} value={summary.messenger} tone="ok" onOpen={() => setSection("notifications")} />
                <MobileLink label={MOBILE_TITLE.password} onOpen={() => setSection("password")} />
                <MobileLink label={MOBILE_TITLE.totp} value={user.totpEnabled ? t("common.on_2") : t("common.off_2")} onOpen={() => setSection("totp")} />
                <MobileLink label={MOBILE_TITLE.sessions} value={summary.sessions ? String(summary.sessions) : ""} onOpen={() => setSection("sessions")} />
              </div>
            </>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="profile-page">
      <ProfileHeader user={user} onLogout={onLogout} />
      <div className="profile-columns">
        <div className="profile-column">
          <ProfileInfoForm profile={page.profile} user={user} message={page.profileMessage} saving={page.savingProfile} setProfile={page.setProfile} onUserUpdated={onUserUpdated} onSubmit={page.saveProfile} />
          <ProfileAppearanceCard user={user} onUserUpdated={onUserUpdated} />
          <ProfileLanguageCard user={user} onUserUpdated={onUserUpdated} />
          <ProfileNotificationsCard />
        </div>
        <div className="profile-column">{security}</div>
      </div>
    </div>
  );
}

function MobileLink({ label, value = "", tone = "", onOpen }: { label: string; value?: string; tone?: string; onOpen: () => void }) {
  return (
    <button type="button" onClick={onOpen}>
      <span>{label}</span>
      {value && <small className={tone}>{value}</small>}
      <Icon name="chevronRight" size={16} strokeWidth={2} />
    </button>
  );
}

// Подписи в списке подэкранов кадра M: привязанный мессенджер и число сессий.
function useProfileSummary(enabled: boolean) {
  const [summary, setSummary] = useState<{ messenger: string; sessions: number }>({ messenger: "", sessions: 0 });
  useEffect(() => {
    if (!enabled) return;
    fetchProfileSessions().then((items) => setSummary((current) => ({ ...current, sessions: items.length }))).catch(() => undefined);
    api<{ items: Array<{ provider: string; bound: boolean }> }>("/api/v1/notifications/messenger-bindings/")
      .then((payload) => {
        const bound = payload.items.find((item) => item.bound);
        setSummary((current) => ({ ...current, messenger: bound ? (bound.provider === "TELEGRAM" ? "Telegram" : "MAX") : "" }));
      })
      .catch(() => undefined);
  }, [enabled]);
  return summary;
}
