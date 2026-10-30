import { useState } from "react";

import { api } from "../../api/client";
import { DeleteIntegrationDialog } from "./DeleteIntegrationDialog";
import { EmptyState } from "../../shared/ui";
import { UnderlineTabs } from "../../shared/ui-controls";
import { ConnectionsTable } from "./ConnectionsTable";
import type { Integration, IntegrationKind } from "./model";
import { ProvidersTable } from "./ProvidersTable";
import { ServicesTab } from "./services/ServicesTab";
import { INTEGRATIONS_TABS, type IntegrationsTab } from "./tabs";
import { t } from "../../i18n";
import "./integrations-tabs.css";

// Таблица интеграций одного рода — раздел экрана «Настройки» (дизайн-базлайн v2,
// кадры N3/N4): подключения и AI-провайдеры — два раздела субменю. У подключений
// три вкладки (Сервисы.dc.html): точки входа диалогов, внешние серверы и сервисы.
// Список грузит страница настроек (счётчики в субменю), форма создания
// открывается primary-кнопкой в шапке раздела.

const TAB_KIND: Record<Exclude<IntegrationsTab, "services">, IntegrationKind> = {
  entry: "MESSENGER",
  servers: "EXTERNAL_SERVER",
};

export function IntegrationsSection({ kind, items, reload, onEdit, tab = "entry", openTab, openServiceConnection }: {
  kind: IntegrationKind;
  items: Integration[];
  reload: () => void;
  onEdit: (integration: Integration) => void;
  tab?: IntegrationsTab;
  openTab?: (tab: IntegrationsTab) => void;
  openServiceConnection?: (id: number) => void;
}) {
  const [testingId, setTestingId] = useState<number | null>(null);
  const [deleting, setDeleting] = useState<Integration | null>(null);

  async function test(integration: Integration) {
    setTestingId(integration.id);
    try {
      await api(`/api/v1/integrations/${integration.id}/test/`, { method: "POST" });
    } catch {
      /* статус придёт из перезагрузки списка */
    } finally {
      setTestingId(null);
      reload();
    }
  }

  async function toggleActive(integration: Integration) {
    try {
      await api(`/api/v1/integrations/${integration.id}/`, {
        method: "PATCH",
        body: JSON.stringify({ isActive: !integration.isActive }),
      });
    } finally {
      reload();
    }
  }

  const rowHandlers = {
    testingId,
    onTest: test,
    onEdit,
    onToggleActive: toggleActive,
    onDelete: (item: Integration) => setDeleting(item),
  };

  if (kind === "LLM_PROVIDER") {
    return (
      <div className="integrations-section">
        {items.length === 0 ? <EmptyState title={t("settings.no_providers_yet_add_openrouter")} /> : <ProvidersTable items={items} {...rowHandlers} />}
        {deleting && <DeleteIntegrationDialog integration={deleting} onClose={() => setDeleting(null)} onDeleted={() => { setDeleting(null); reload(); }} />}
      </div>
    );
  }

  const shown = tab === "services" ? [] : items.filter((item) => item.kind === TAB_KIND[tab]);
  return (
    <div className="integrations-section">
      <UnderlineTabs className="integrations-tabs" items={INTEGRATIONS_TABS} value={tab} onChange={(next) => openTab?.(next)} />
      {tab === "services" ? (
        <ServicesTab openConnection={(id) => openServiceConnection?.(id)} />
      ) : shown.length === 0 ? (
        <EmptyState title={tab === "entry" ? t("settings.no_connections_yet_add_bot") : t("ai.tools_empty")} />
      ) : (
        <ConnectionsTable items={shown} {...rowHandlers} />
      )}
      {deleting && <DeleteIntegrationDialog integration={deleting} onClose={() => setDeleting(null)} onDeleted={() => { setDeleting(null); reload(); }} />}
    </div>
  );
}
