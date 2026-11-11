import { isManager } from "../../../auth/access";
import { t } from "../../../i18n";
import { EmptyState } from "../../../shared/ui";
import type { SessionUser } from "../../../types";
import { IntegrationWorkspaceLayout } from "../IntegrationWorkspaceLayout";
import { ServiceCardPage } from "./card/ServiceCardPage";
import { ServicesTab } from "./ServicesTab";

export function ServicesPage({ user, connectionId, openConnection, openScenario, onBack }: {
  user: SessionUser;
  connectionId?: number;
  openConnection: (id: number) => void;
  openScenario: (id: string) => void;
  onBack: () => void;
}) {
  if (!isManager(user)) return <EmptyState title={t("settings.settings_available_owner_administrators")} />;
  return <IntegrationWorkspaceLayout>
    {connectionId ? <ServiceCardPage key={`${user.organizationPublicId}:${connectionId}`} connectionId={connectionId}
      onBack={onBack} onOpenScenario={openScenario} /> : <>
      <header className="settings-head"><div><h2>{t("common.integrations")}</h2><p>{t("services.section_lead")}</p></div></header>
      <ServicesTab key={user.organizationPublicId} openConnection={openConnection} />
    </>}
  </IntegrationWorkspaceLayout>;
}
