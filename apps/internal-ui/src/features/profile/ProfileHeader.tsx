import type { SessionUser } from "../../types";
import { Icon } from "../../shared/icons";
import { Avatar, RoleBadge } from "../../shared/ui";
import type { ProfileFormState } from "./types";

export function ProfileHeader({ profile, user, onLogout }: { profile: ProfileFormState; user: SessionUser; onLogout: () => void }) {
  return (
    <section className="profile-header-card">
      <Avatar user={user} />
      <div className="profile-header-main">
        <div><h1>{profile.fullName || profile.email}</h1><RoleBadge role={user.role} /></div>
        <p>{profile.email}</p>
      </div>
      <button className="danger-outline" type="button" onClick={onLogout}><Icon name="logout" size={15} />Выйти</button>
    </section>
  );
}
