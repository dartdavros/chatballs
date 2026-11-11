import { useEffect } from "react";
import { useIntegrations } from "../features/settings/useIntegrations";
import { ServerPageLoading } from "../features/integrations/external/ServerPageLoading";
import { t } from "../i18n";
import { Icon } from "../shared/icons";
import { ContentState } from "../shared/ui";
import { Button } from "../shared/ui-controls";
import type { Integration } from "../features/integrations/model";
import type { RouteKey } from "../types";

export function integrationDestination(integration: Pick<Integration, "kind" | "provider" | "id">): {
  route: RouteKey;
  id: number | null;
} {
  if (integration.kind === "EXTERNAL_SERVER") return { route: "externalServerSettings", id: integration.id };
  if (integration.provider === "WEB") return { route: "webIntegrationSettings", id: integration.id };
  if (integration.kind === "LLM_PROVIDER" || integration.kind === "SPEECH_PROVIDER") return { route: "aiProviders", id: null };
  return { route: integration.provider === "EMAIL" ? "emailIntegrations" : "messengers", id: null };
}

/** Старый URL не различал виджеты и серверы; тип берём из существующего подключения. */
export function LegacyIntegrationRoute({ id, onResolved, onBack }: {
  id: number;
  onResolved: (route: RouteKey, id: number | null) => void;
  onBack: () => void;
}) {
  const list = useIntegrations(true);
  const integration = list.items.find((item) => item.id === id);
  useEffect(() => {
    if (list.loading || list.failed || !integration) return;
    const destination = integrationDestination(integration);
    onResolved(destination.route, destination.id);
  }, [integration, list.failed, list.loading, onResolved]);
  if (list.loading || integration && !list.failed) return <ServerPageLoading />;
  return <ContentState className="server-page-state" icon={<Icon name="plug" size={18} />}
    title={t(list.failed ? "navigation.connections_load_failed" : "navigation.connection_not_found")}
    text={t(list.failed ? "navigation.connections_load_failed_hint" : "navigation.connection_not_found_hint")}
    action={list.failed ? <Button variant="secondary" onClick={list.reload}>{t("common.try_again")}</Button>
      : <button className="link is-strong" type="button" onClick={onBack}>{t("navigation.widgets")}</button>} />;
}
