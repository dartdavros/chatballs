import type { SessionUser } from "../../types";
import { Avatar, RoleBadge } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import type { ProfileFormState } from "./types";

export function ProfileHeader({ profile, user, onLogout }: { profile: ProfileFormState; user: SessionUser; onLogout: () => void }) {
  return (
    <section className="profile-header-card">
      <Avatar user={user} />
      <div className="profile-header-main">
        <div><h1>{profile.fullName || profile.email}</h1><RoleBadge role={user.role} /></div>
        <p>{profile.email}</p>
      </div>
      <Button icon="logout" type="button" variant="danger-outline" onClick={onLogout}>Выйти</Button>
    </section>
  );
}
