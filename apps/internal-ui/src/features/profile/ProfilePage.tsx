import type { SessionUser } from "../../types";
import { ProfileHeader } from "./ProfileHeader";
import { ProfileInfoForm } from "./ProfileInfoForm";
import { ProfileNotificationsCard } from "./ProfileNotificationsCard";
import { ProfilePasswordForm } from "./ProfilePasswordForm";
import { ProfileSessionsCard } from "./ProfileSessionsCard";
import { ProfileTotpCard } from "./ProfileTotpCard";
import { useProfilePage } from "./useProfilePage";

export function ProfilePage({ user, onUserUpdated, reload, onLogout }: { user: SessionUser; onUserUpdated: (user: SessionUser) => void; reload: () => void; onLogout: () => void }) {
  const profilePage = useProfilePage({ user, onUserUpdated, reload });

  return (
    <div className="profile-stack">
      <ProfileHeader profile={profilePage.profile} user={user} onLogout={onLogout} />
      <ProfileInfoForm profile={profilePage.profile} user={user} message={profilePage.profileMessage} saving={profilePage.savingProfile} setProfile={profilePage.setProfile} onSubmit={profilePage.saveProfile} />
      <ProfilePasswordForm passwords={profilePage.passwords} message={profilePage.passwordMessage} mismatch={profilePage.passwordMismatch} ready={profilePage.passwordReady} saving={profilePage.savingPassword} setPasswords={profilePage.setPasswords} onSubmit={profilePage.updatePassword} />
      <ProfileNotificationsCard />
      <ProfileTotpCard user={user} message={profilePage.totpMessage} saving={profilePage.savingTotp} onToggle={profilePage.toggleTotp} />
      <ProfileSessionsCard message={profilePage.sessionsMessage} revoking={profilePage.revokingSessions} onRevoke={profilePage.revokeOtherSessions} />
    </div>
  );
}
