import { useState } from "react";

import { fmt, t } from "../../i18n";
import type { SectionMenuItem } from "../../shared/SectionMenu";
import { IntegrationPageLayout } from "./IntegrationPageLayout";
import { EmptyState, LoadingState } from "../../shared/ui";
import { DeleteIntegrationDialog } from "./DeleteIntegrationDialog";
import { WebIntegrationBasics } from "./WebIntegrationBasics";
import { WebIntegrationHeader } from "./WebIntegrationHeader";
import { useWebIntegration } from "./useWebIntegration";
import { SiteFieldsSection } from "./site-fields/SiteFieldsSection";
import { WebIntegrationAppearance } from "./appearance/WebIntegrationAppearance";
import { PreChatSection } from "./pre-chat/PreChatSection";
import { SiteEventSection } from "./site-events/SiteEventSection";

type Section = "basics" | "fields" | "form" | "events" | "look" | "danger";

const sections: SectionMenuItem<Section>[] = [
  { key: "basics", label: t("portals.basics"), icon: "settings" },
  { key: "fields", label: t("settings.site_data"), icon: "code" },
  { key: "form", label: t("settings.pre_chat_form"), icon: "form" },
  { key: "events", label: t("site_events.section"), icon: "message" },
  { key: "look", label: t("common.appearance"), icon: "paint", divider: true },
  { key: "danger", label: t("settings.delete_connection"), icon: "trash", danger: true },
];

export function WebIntegrationPage({ integrationId, onBack }: {
  integrationId: number;
  onBack: () => void;
}) {
  const { integration, loading, failed, setIntegration } = useWebIntegration(integrationId);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [section, setSection] = useState<Section>("basics");
  const [fieldCount, setFieldCount] = useState<number>();
  const [formEnabled, setFormEnabled] = useState<boolean>();

  if (loading) return <LoadingState />;
  if (failed) return <EmptyState title={t("settings.could_not_load_integrations")} />;
  if (!integration) return <EmptyState title={t("settings.web_integration_not_found")} />;

  return (
    <>
      <IntegrationPageLayout
        className={section === "events" ? "site-event-settings" : ""}
        header={<WebIntegrationHeader integration={integration} onBack={onBack} />}
        items={sections.map((item) => {
          if (item.key === "fields") return { ...item, hint: { text: fmt.number(fieldCount ?? integration.config.fields?.length ?? 0) } };
          if (item.key === "form" && (formEnabled ?? integration.config.preChat?.enabled)) return { ...item, hint: { text: t("pre_chat.on") } };
          return item;
        })}
        activeKey={section}
        note={t("settings.web_changes_apply_after_save")}
        onSelect={(next) => { if (next === "danger") setConfirmingDelete(true); else setSection(next); }}
      >
        <div className="portal-settings-inner" hidden={section !== "basics"}>
          <div className="portal-settings-heading">
            <h3>{t("portals.basics")}</h3>
          </div>
          <WebIntegrationBasics key={integration.id} integration={integration} onSaved={setIntegration} />
        </div>
        <div hidden={section !== "fields"}>
          <SiteFieldsSection key={integration.id} integration={integration} onSaved={setIntegration} onCount={setFieldCount} />
        </div>
        <div hidden={section !== "form"}>
          <PreChatSection key={integration.id} integration={integration} onSaved={setIntegration} onEnabled={setFormEnabled} />
        </div>
        {section === "look" && <WebIntegrationAppearance key={integration.id} integration={integration} onSaved={setIntegration} />}
        {section === "events" && <SiteEventSection key={integration.id} integration={integration} onSaved={setIntegration} />}
      </IntegrationPageLayout>
      {confirmingDelete && <DeleteIntegrationDialog integration={integration} onClose={() => setConfirmingDelete(false)} onDeleted={onBack} />}
    </>
  );
}
