import { useState } from "react";
import { api } from "../../api/client";
import { t } from "../../i18n";
import { EmptyState, LoadingState } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import { ConnectionsTable } from "./ConnectionsTable";
import { DeleteIntegrationDialog } from "./DeleteIntegrationDialog";
import type { Integration } from "./model";
import { ProvidersTable } from "./ProvidersTable";

export function IntegrationList({ items, providers = false, servers = false, loading = false, failed = false, empty, reload, onEdit }: {
  items: Integration[];
  providers?: boolean;
  servers?: boolean;
  loading?: boolean;
  failed?: boolean;
  empty: string;
  reload: () => void;
  onEdit: (integration: Integration) => void;
}) {
  const [testingId, setTestingId] = useState<number | null>(null);
  const [deleting, setDeleting] = useState<Integration | null>(null);
  const [error, setError] = useState("");

  async function test(integration: Integration) {
    setTestingId(integration.id); setError("");
    try { await api(`/api/v1/integrations/${integration.id}/test/`, { method: "POST" }); }
    catch (caught) { setError(caught instanceof Error ? caught.message : t("common.request_failed")); }
    finally { setTestingId(null); reload(); }
  }

  async function toggleActive(integration: Integration) {
    setError("");
    try {
      await api(`/api/v1/integrations/${integration.id}/`, {
        method: "PATCH", body: JSON.stringify({ isActive: !integration.isActive }),
      });
    } catch (caught) { setError(caught instanceof Error ? caught.message : t("common.request_failed")); }
    finally { reload(); }
  }

  const handlers = { testingId, onTest: test, onEdit, onToggleActive: toggleActive, onDelete: setDeleting };
  return <div className="integrations-section">
    {error && <p className="integration-form-error" role="alert">{error}</p>}
    {loading ? <LoadingState /> : failed ? <>
      <EmptyState title={t("navigation.connections_load_failed")} />
      <Button variant="secondary" onClick={reload}>{t("common.try_again")}</Button>
    </> : items.length === 0 ? <EmptyState title={empty} /> : providers
      ? <ProvidersTable items={items} {...handlers} />
      : <ConnectionsTable items={items} context={servers ? "servers" : "channels"} {...handlers} />}
    {deleting && <DeleteIntegrationDialog integration={deleting} onClose={() => setDeleting(null)}
      onDeleted={() => { setDeleting(null); reload(); }} />}
  </div>;
}
