import { EmptyState, LoadingState } from "../../shared/ui";
import { SalesClientsEmpty } from "./clients/SalesClientsEmpty";
import { SalesClientsFilters } from "./clients/SalesClientsFilters";
import { SalesClientsHeader } from "./clients/SalesClientsHeader";
import { SalesClientsTable } from "./clients/SalesClientsTable";
import { exportClientsCsv } from "./clients/exportClientsCsv";
import { useClientsData } from "./clients/useClientsData";
import { useSalesClients } from "./clients/useSalesClients";

// «Контакты» (дизайн-базлайн v2, кадры K1/K2/S1).
export function SalesClientsPage({ openClient, openIntegrations }: { openClient: (id: number) => void; openIntegrations: () => void }) {
  const { clients: data, loading, error } = useClientsData();
  const clients = useSalesClients(data);

  if (loading) return <div className="sales-clients-page"><LoadingState /></div>;
  if (error) return <div className="sales-clients-page"><EmptyState title="Не удалось загрузить контакты" /></div>;

  return (
    <div className="sales-clients-page">
      <SalesClientsHeader shownCount={clients.filteredCount} totalCount={data.length} filtered={clients.filtered} onExport={() => exportClientsCsv(clients.filteredRows)} />
      {data.length === 0 ? (
        <SalesClientsEmpty onOpenIntegrations={openIntegrations} />
      ) : (
        <>
          <SalesClientsFilters clients={clients} salesClients={data} />
          <SalesClientsTable clients={clients} openClient={openClient} />
        </>
      )}
    </div>
  );
}
