import type { SessionUser } from "../../types";
import { ProfileNotificationsCard } from "../profile/ProfileNotificationsCard";
import { ProfilePasswordForm } from "../profile/ProfilePasswordForm";
import { ProfileSessionsCard } from "../profile/ProfileSessionsCard";
import { ProfileTotpCard } from "../profile/ProfileTotpCard";
import { useProfilePage } from "../profile/useProfilePage";

export function SettingsPage({ user, onUserUpdated, reload }: { user: SessionUser; onUserUpdated: (user: SessionUser) => void; reload: () => void }) {
  const profilePage = useProfilePage({ user, onUserUpdated, reload });

  return (
    <div className="profile-stack">
      <ProfilePasswordForm passwords={profilePage.passwords} message={profilePage.passwordMessage} mismatch={profilePage.passwordMismatch} ready={profilePage.passwordReady} saving={profilePage.savingPassword} setPasswords={profilePage.setPasswords} onSubmit={profilePage.updatePassword} />
      <ProfileNotificationsCard />
      <ProfileTotpCard user={user} message={profilePage.totpMessage} saving={profilePage.savingTotp} onToggle={profilePage.toggleTotp} />
      <ProfileSessionsCard message={profilePage.sessionsMessage} revoking={profilePage.revokingSessions} onRevoke={profilePage.revokeOtherSessions} />
    </div>
  );
}
