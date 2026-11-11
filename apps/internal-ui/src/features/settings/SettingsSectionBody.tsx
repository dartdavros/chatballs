import { ParticipantLimitCard } from "./ParticipantLimitCard";
import { RatingSettingsCard } from "../ratings/RatingSettingsCard";
import { RuleSettingsCard } from "../handling-rules/RuleSettingsCard";
import { QualitySettings } from "../quality/QualitySettings";
import { TransferSettings } from "./transfer/TransferSettings";
import type { ReactNode } from "react";
import type { EmployeeGroup, SessionUser } from "../../types";
import { OrganizationSettingsForm } from "../administration/OrganizationSettingsForm";
import { canManageSettings } from "../administration/model";
import { useAdministration } from "../administration/useAdministration";
import { EmptyState, LoadingState } from "../../shared/ui";
import { DemoDataCard } from "./DemoDataCard";
import { CommunicationSettingsCard } from "./CommunicationSettingsCard";
import { PlatformSettingsCard } from "./PlatformSettingsCard";
import { StorageSettingsCard } from "./StorageSettingsCard";
import { GroupsSettingsCard } from "./GroupsSettingsCard";
import { QueuePolicyCard } from "./QueuePolicyCard";
import { ReplyTemplateLibrary } from "../reply-templates/ReplyTemplateLibrary";
import type { SettingsSectionKey } from "./sections";
import { t } from "../../i18n";
import { RunRetention } from "../integrations/runs/RunRetention";

export function SettingsSectionBody({ section, user, onUserUpdated, reload, groups, onTemplatesChanged, openJournal }: {
  section: SettingsSectionKey; user: SessionUser; onUserUpdated: (user: SessionUser) => void; reload: () => void;
  groups: EmployeeGroup[];
  onTemplatesChanged: () => void;
  openJournal: () => void;
}): ReactNode {
  if (section === "organization") return <OrganizationSection user={user} onUserUpdated={onUserUpdated} />;
  if (section === "groups") return <GroupsSettingsCard groups={groups} reload={reload} />;
  if (section === "ratings") return <RatingSettingsCard key={user.organizationPublicId} />;
  if (section === "rules") return <RuleSettingsCard key={user.organizationPublicId} openJournal={openJournal} />;
  if (section === "quality") return <QualitySettings key={user.organizationPublicId} />;
  if (section === "transfer") return <><TransferSettings /><ParticipantLimitCard canManage={canManageSettings(user)} /></>;
  if (section === "queue") return <QueuePolicyCard canManage={canManageSettings(user)} />;
  if (section === "communication") return <CommunicationSettingsCard canManage={canManageSettings(user)} canManageRelay={user.isInstanceAdmin} />;
  if (section === "platform") return <PlatformSettingsCard canManage={user.isInstanceAdmin} organizationName={user.organizationName} />;
  if (section === "storage") return <StorageSettingsCard canManage={user.isInstanceAdmin} />;
  if (section === "demo") return <DemoDataCard reload={reload} />;
  if (section === "templates") return <ReplyTemplateLibrary onChanged={onTemplatesChanged} />;
  return null;
}

function OrganizationSection({ user, onUserUpdated }: { user: SessionUser; onUserUpdated: (user: SessionUser) => void }) {
  const page = useAdministration({ section: "organization", user, onUserUpdated });
  if (page.loading) return <LoadingState />;
  if (!page.organization) return <EmptyState title={page.error || t("settings.could_not_load_settings")} />;
  return <><OrganizationSettingsForm organization={page.organization} canManage={canManageSettings(user)} saving={page.saving}
    message={page.message} error={page.error} timezones={page.timezones} languages={page.languages} onChange={page.setOrganization}
    onSave={() => void page.save()} onUploadLogo={file => void page.uploadLogo(file)} onRemoveLogo={() => void page.removeLogo()} />{canManageSettings(user) && <RunRetention />}</>;
}
