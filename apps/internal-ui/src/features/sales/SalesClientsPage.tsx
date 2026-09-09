import { useEffect, useState } from "react";

import { EmptyState, LoadingState } from "../../shared/ui";
import { useAiAgents } from "../ai/useAiAgents";
import { SalesClientsEmpty } from "./clients/SalesClientsEmpty";
import { SalesClientsFilters } from "./clients/SalesClientsFilters";
import { SalesClientsHeader } from "./clients/SalesClientsHeader";
import { SalesClientsTable } from "./clients/SalesClientsTable";
import { fetchClientsForExport, fetchClientsTotal } from "./clients/api";
import { exportClientsCsv } from "./clients/exportClientsCsv";
import { toSalesClient, toSalesClientRow } from "./clients/model";
import { useSalesClients } from "./clients/useSalesClients";
import { t } from "../../i18n";

// «Контакты» (дизайн-базлайн v2, кадры K1/K2/S1). Страница списка — серверная.
export function SalesClientsPage({ openClient, openIntegrations }: { openClient: (id: number) => void; openIntegrations: () => void }) {
  const clients = useSalesClients();
  const { agents } = useAiAgents();
  // Счётчик «6 из 128»: знаменатель — весь список без фильтров.
  const [totalCount, setTotalCount] = useState<number | null>(null);
  useEffect(() => {
    let active = true;
    void fetchClientsTotal()
      .then((total) => { if (active) setTotalCount(total); })
      .catch(() => undefined);
    return () => { active = false; };
  }, []);

  async function exportCsv() {
    const rows = await fetchClientsForExport(clients.request);
    exportClientsCsv(rows.map((row) => toSalesClientRow(toSalesClient(row))));
  }

  if (clients.loading && clients.rows.length === 0 && totalCount === null) {
    return <div className="sales-clients-page"><LoadingState /></div>;
  }
  if (clients.errorText) {
    return <div className="sales-clients-page"><EmptyState title={t("sales.could_not_load_contacts")} /></div>;
  }

  return (
    <div className="sales-clients-page">
      <SalesClientsHeader
        shownCount={clients.total}
        totalCount={totalCount ?? clients.total}
        filtered={clients.filtered}
        onExport={() => void exportCsv()}
      />
      {(totalCount ?? 0) === 0 && !clients.filtered ? (
        <SalesClientsEmpty onOpenIntegrations={openIntegrations} />
      ) : (
        <>
          <SalesClientsFilters clients={clients} agents={agents.map((agent) => ({ id: agent.id, name: agent.name }))} />
          <SalesClientsTable clients={clients} openClient={openClient} />
        </>
      )}
    </div>
  );
}
