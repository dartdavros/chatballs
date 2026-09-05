import { EmptyState, LoadingState } from "../../shared/ui";
import { SalesClientsFilters } from "./clients/SalesClientsFilters";
import { SalesClientsHeader } from "./clients/SalesClientsHeader";
import { SalesClientsTable } from "./clients/SalesClientsTable";
import { exportClientsCsv } from "./clients/exportClientsCsv";
import { useClientsData } from "./clients/useClientsData";
import { useSalesClients } from "./clients/useSalesClients";

export function SalesClientsPage({ openClient }: { openClient: (id: number) => void }) {
  const { clients: data, loading, error } = useClientsData();
  const clients = useSalesClients(data);

  return (
    <>
      <SalesClientsHeader shownCount={clients.filteredCount} totalCount={data.length} onExport={() => exportClientsCsv(clients.filteredRows)} />
      {loading ? (
        <LoadingState />
      ) : error ? (
        <EmptyState title="Не удалось загрузить контакты" />
      ) : (
        <>
          <SalesClientsFilters clients={clients} salesClients={data} />
          <SalesClientsTable clients={clients} openClient={openClient} />
        </>
      )}
    </>
  );
}
