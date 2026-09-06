import type { SessionUser } from "../../types";
import { Avatar } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import { monthYear } from "../../shared/utils";

// Шапка «Профиля» (дизайн-базлайн v2, кадры P1/P2): фото 72 · имя с бейджем
// роли · email, дата вступления и группы · «Выйти». Роль показана бейджем,
// отдельного поля «Роль» в форме нет.

const ROLE_LABEL: Record<SessionUser["role"], string> = {
  OWNER: "Владелец",
  ADMIN: "Администратор",
  EMPLOYEE: "Сотрудник",
};

export function ProfileHeader({ user, compact = false, onLogout }: { user: SessionUser; compact?: boolean; onLogout: () => void }) {
  const groups = user.groups.map((group) => group.name).join(", ");
  return (
    <header className="profile-header">
      <span className="profile-header-photo"><Avatar user={user} /></span>
      <div className="profile-header-main">
        <div>
          <h2>{user.fullName || user.email}</h2>
          <b className={`profile-role ${user.role === "EMPLOYEE" ? "is-muted" : ""}`}>{ROLE_LABEL[user.role]}</b>
        </div>
        {/* Кадр M: на узком экране под именем только email. */}
        <p>
          {user.email}
          {!compact && user.joinedAt ? ` · в организации с ${monthYear(user.joinedAt)}` : ""}
          {!compact && groups ? ` · группы: ${groups}` : ""}
        </p>
      </div>
      <Button icon="logout" type="button" variant="danger-outline" onClick={onLogout}>Выйти</Button>
    </header>
  );
}
