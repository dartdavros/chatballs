import type { ReactNode } from "react";

import { isManager } from "../../auth/access";
import type { EmployeeGroup, SessionUser } from "../../types";
import { OrganizationSettingsForm } from "../administration/OrganizationSettingsForm";
import { canManageSettings } from "../administration/model";
import { useAdministration } from "../administration/useAdministration";
import { IntegrationsSection } from "../integrations/IntegrationsSection";
import { ProfileAppearanceCard } from "../profile/ProfileAppearanceCard";
import { ProfileAvatarCard } from "../profile/ProfileAvatarCard";
import { ProfileNotificationsCard } from "../profile/ProfileNotificationsCard";
import { ProfilePasswordForm } from "../profile/ProfilePasswordForm";
import { ProfileSessionsCard } from "../profile/ProfileSessionsCard";
import { ProfileTotpCard } from "../profile/ProfileTotpCard";
import { useProfilePage } from "../profile/useProfilePage";
import { EmptyState, LoadingState, PageHeader } from "../../shared/ui";
import type { RouteKey } from "../../types";
import { Icon } from "../../shared/icons";
import { DemoDataCard } from "./DemoDataCard";
import { StorageSettingsCard } from "./StorageSettingsCard";
import { GroupsSettingsCard } from "./GroupsSettingsCard";

// «Настройки» (SPEC-HUB-0031 §8.6): один экран с вертикальными секциями —
// Организация · Группы · AI-провайдер · Интеграции · Профиль. Отдельные
// разделы «Организация» и «Интеграции» упразднены. Сотруднику доступна
// только профильная часть (тема, акцент, безопасность).

export function SettingsPage({ user, onUserUpdated, reload, groups = [], setRoute }: { user: SessionUser; onUserUpdated: (user: SessionUser) => void; reload: () => void; groups?: EmployeeGroup[]; setRoute: (route: RouteKey) => void }) {
  const profilePage = useProfilePage({ user, onUserUpdated, reload });
  const manager = isManager(user);

  const profileSections = (
    <>
      <ProfileAvatarCard user={user} onUserUpdated={onUserUpdated} />
      <ProfileAppearanceCard user={user} onUserUpdated={onUserUpdated} />
      <ProfilePasswordForm passwords={profilePage.passwords} message={profilePage.passwordMessage} mismatch={profilePage.passwordMismatch} ready={profilePage.passwordReady} saving={profilePage.savingPassword} setPasswords={profilePage.setPasswords} onSubmit={profilePage.updatePassword} />
      <ProfileNotificationsCard />
      <ProfileTotpCard user={user} message={profilePage.totpMessage} saving={profilePage.savingTotp} onToggle={profilePage.toggleTotp} />
      <ProfileSessionsCard message={profilePage.sessionsMessage} revoking={profilePage.revokingSessions} onRevoke={profilePage.revokeOtherSessions} />
    </>
  );

  if (!manager) {
    return <div className="profile-stack"><PageHeader title="Настройки" />{profileSections}</div>;
  }

  return (
    <div className="profile-stack settings-screen">
      <PageHeader title="Настройки" />
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
      <SettingsSection title="Хранилище файлов" note="Вложения, голосовые, фото и логотипы — на диске установки или во внешнем S3">
        <StorageSettingsCard canManage={canManageSettings(user)} />
      </SettingsSection>
      <SettingsSection title="Знания и аудит" note="База знаний агентов и журнал действий — отдельными экранами">
        <div className="settings-links">
          <button className="link has-icon" type="button" onClick={() => setRoute("aiKnowledge")}><Icon name="folder" size={15} />База знаний</button>
          <button className="link has-icon" type="button" onClick={() => setRoute("administrationAudit")}><Icon name="list" size={15} />Аудит действий</button>
        </div>
      </SettingsSection>
      <SettingsSection title="Демо-данные" note="Посмотреть систему в работе на вымышленной организации">
        <DemoDataCard reload={reload} />
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
