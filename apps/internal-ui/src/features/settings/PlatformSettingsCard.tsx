import { useEffect, useState } from "react";

import { t } from "../../i18n";
import { UpdatesCard } from "../updates/UpdatesCard";
import { AddressCard } from "./AddressCard";
import { EmailCard } from "./EmailCard";
import { loadInstance, type InstancePayload } from "./instance";
import { LanguageCard } from "./LanguageCard";
import { ToolsNetworkCard } from "./ToolsNetworkCard";

export function PlatformSettingsCard({ canManage, organizationName }: { canManage: boolean; organizationName: string }) {
  const [current, setCurrent] = useState<InstancePayload | null>(null);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    loadInstance()
      .then(setCurrent)
      .catch(() => setLoadError(t("settings.could_not_load_installation_settings")));
  }, []);

  if (loadError) return <div className="settings-section-error">{loadError}</div>;
  if (!current) return null;

  return (
    <>
      <UpdatesCard
        canManage={canManage}
        externalChecksEnabled={current.externalChecksEnabled}
        onSettingsSaved={setCurrent}
      />
      <AddressCard canManage={canManage} current={current} onSaved={setCurrent} />
      <LanguageCard canManage={canManage} current={current} onSaved={setCurrent} />
      <EmailCard canManage={canManage} current={current} onSaved={setCurrent} />
      {/* Настройку локальной сети сервер отдаёт только администратору установки. */}
      {canManage && <ToolsNetworkCard organizationName={organizationName} />}
      <p className="settings-section-note">{t("settings.platform_instance_admin_only")}</p>
    </>
  );
}
