import type { ReactNode } from "react";

import { isManager } from "../../auth/access";
import type { EmployeeGroup, SessionUser } from "../../types";
import { OrganizationSettingsForm } from "../administration/OrganizationSettingsForm";
import { canManageSettings } from "../administration/model";
import { useAdministration } from "../administration/useAdministration";
import { IntegrationsSection } from "../integrations/IntegrationsSection";
import { ProfileAppearanceCard } from "../profile/ProfileAppearanceCard";
import { ProfileNotificationsCard } from "../profile/ProfileNotificationsCard";
import { ProfilePasswordForm } from "../profile/ProfilePasswordForm";
import { ProfileSessionsCard } from "../profile/ProfileSessionsCard";
import { ProfileTotpCard } from "../profile/ProfileTotpCard";
import { useProfilePage } from "../profile/useProfilePage";
import { EmptyState, LoadingState } from "../../shared/ui";
import { GroupsSettingsCard } from "./GroupsSettingsCard";

// «Настройки» (SPEC-HUB-0031 §8.6): один экран с вертикальными секциями —
// Организация · Группы · AI-провайдер · Интеграции · Профиль. Отдельные
// разделы «Организация» и «Интеграции» упразднены. Сотруднику доступна
// только профильная часть (тема, акцент, безопасность).

export function SettingsPage({ user, onUserUpdated, reload, groups = [] }: { user: SessionUser; onUserUpdated: (user: SessionUser) => void; reload: () => void; groups?: EmployeeGroup[] }) {
  const profilePage = useProfilePage({ user, onUserUpdated, reload });
  const manager = isManager(user);

  const profileSections = (
    <>
      <ProfileAppearanceCard user={user} onUserUpdated={onUserUpdated} />
      <ProfilePasswordForm passwords={profilePage.passwords} message={profilePage.passwordMessage} mismatch={profilePage.passwordMismatch} ready={profilePage.passwordReady} saving={profilePage.savingPassword} setPasswords={profilePage.setPasswords} onSubmit={profilePage.updatePassword} />
      <ProfileNotificationsCard />
      <ProfileTotpCard user={user} message={profilePage.totpMessage} saving={profilePage.savingTotp} onToggle={profilePage.toggleTotp} />
      <ProfileSessionsCard message={profilePage.sessionsMessage} revoking={profilePage.revokingSessions} onRevoke={profilePage.revokeOtherSessions} />
    </>
  );

  if (!manager) {
    return <div className="profile-stack">{profileSections}</div>;
  }

  return (
    <div className="profile-stack settings-screen">
      <SettingsSection title="Организация">
        <OrganizationSection user={user} onUserUpdated={onUserUpdated} />
      </SettingsSection>
      <SettingsSection title="Группы">
        <GroupsSettingsCard groups={groups} reload={reload} />
      </SettingsSection>
      <SettingsSection title="AI-провайдер" note="BYOK: ключи вашей организации для ответов агентов и расшифровки голосовых">
        <IntegrationsSection kind="LLM_PROVIDER" />
      </SettingsSection>
      <SettingsSection title="Интеграции" note="Боты, почта и Web-виджет — точки входа диалогов">
        <IntegrationsSection kind="MESSENGER" />
      </SettingsSection>
      <SettingsSection title="Профиль">{profileSections}</SettingsSection>
    </div>
  );
}

function SettingsSection({ title, note, children }: { title: string; note?: string; children: ReactNode }) {
  return (
    <section className="settings-section">
      <header className="settings-section-head">
        <h2>{title}</h2>
        {note && <span>{note}</span>}
      </header>
      {children}
    </section>
  );
}

function OrganizationSection({ user, onUserUpdated }: { user: SessionUser; onUserUpdated: (user: SessionUser) => void }) {
  const page = useAdministration({ section: "organization", user, onUserUpdated });
  if (page.loading) return <LoadingState />;
  if (!page.organization) return <EmptyState title={page.error || "Не удалось загрузить настройки"} />;
  return (
    <OrganizationSettingsForm
      organization={page.organization}
      canManage={canManageSettings(user)}
      saving={page.saving}
      message={page.message}
      error={page.error}
      timezones={page.timezones}
      onChange={page.setOrganization}
      onSave={() => void page.save()}
      onUploadLogo={(file) => void page.uploadLogo(file)}
      onRemoveLogo={() => void page.removeLogo()}
    />
  );
}
