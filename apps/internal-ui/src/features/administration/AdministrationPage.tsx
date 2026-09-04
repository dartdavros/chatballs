import { EmptyState, LoadingState, PageHeader } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import type { SessionUser } from "../../types";
import { AuditTable } from "./AuditTable";
import {
  administrationSection,
  canManageSettings,
  type AdministrationRoute,
} from "./model";
import { OrganizationSettingsForm } from "./OrganizationSettingsForm";
import { useAdministration } from "./useAdministration";

export function AdministrationPage({
  route,
  user,
  onUserUpdated,
}: {
  route: AdministrationRoute;
  user: SessionUser;
  onUserUpdated: (user: SessionUser) => void;
}) {
  const section = administrationSection(route);
  const page = useAdministration({ section, user, onUserUpdated });
  const header = (
    <PageHeader
      title="Администрирование"
      text="Настройки организации и журнал действий"
    />
  );

  if (page.loading) {
    return <div className="administration-page">{header}<LoadingState /></div>;
  }
  if (section === "organization" && !page.organization) {
    return (
      <div className="administration-page">
        {header}
        <EmptyState title={page.error || "Не удалось загрузить настройки"} />
        <Button variant="secondary" onClick={() => void page.reload()}>Повторить</Button>
      </div>
    );
  }

  return (
    <div className="administration-page">
      {header}
      {section === "organization" && page.organization && (
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
      )}
      {section === "audit" && <AuditTable events={page.audit} />}
    </div>
  );
}
