import type { SessionUser } from "../../types";
import { ProfileHeader } from "./ProfileHeader";
import { ProfileInfoForm } from "./ProfileInfoForm";
import { useProfilePage } from "./useProfilePage";

export function ProfilePage({ user, onUserUpdated, reload, onLogout }: { user: SessionUser; onUserUpdated: (user: SessionUser) => void; reload: () => void; onLogout: () => void }) {
  const profilePage = useProfilePage({ user, onUserUpdated, reload });

  return (
    <div className="profile-stack">
      <ProfileHeader profile={profilePage.profile} user={user} onLogout={onLogout} />
      <ProfileInfoForm profile={profilePage.profile} user={user} message={profilePage.profileMessage} saving={profilePage.savingProfile} setProfile={profilePage.setProfile} onSubmit={profilePage.saveProfile} />
    </div>
  );
}
