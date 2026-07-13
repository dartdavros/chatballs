import type { AccessProfile } from "../../types";

export function AccessProfileList({ profiles, selectedId, select }: { profiles: AccessProfile[]; selectedId: number | null; select: (id: number) => void }) {
  return (
    <aside className="access-profile-list">
      {profiles.map((profile) => (
        <button className={selectedId === profile.id ? "selected" : ""} type="button" onClick={() => select(profile.id)} key={profile.id}>
          <span className="access-profile-card-title"><strong>{profile.name}</strong>{profile.isSystem && <b>SYSTEM</b>}{!profile.isActive && <em>ОТКЛ.</em>}</span>
          <span className="access-profile-description">{profile.description}</span>
          <span className="access-profile-meta"><i>{profile.capabilities.length} capability</i><i>{profile.assignedCount} назнач.</i></span>
        </button>
      ))}
    </aside>
  );
}
