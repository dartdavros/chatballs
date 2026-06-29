import { EmptyState, LoadingState } from "../../shared/ui";
import { SalesClientsFilters } from "./clients/SalesClientsFilters";
import { SalesClientsHeader } from "./clients/SalesClientsHeader";
import { SalesClientsTable } from "./clients/SalesClientsTable";
import { useClientsData } from "./clients/useClientsData";
import { useSalesClients } from "./clients/useSalesClients";

export function SalesClientsPage({ openClient }: { openClient: () => void }) {
  const { clients: data, loading, error } = useClientsData();
  const clients = useSalesClients(data);

  return (
    <>
      <SalesClientsHeader shownCount={clients.rows.length} />
      {loading ? (
        <LoadingState />
      ) : error ? (
        <EmptyState title="Не удалось загрузить клиентов" />
      ) : (
        <>
          <SalesClientsFilters clients={clients} />
          <SalesClientsTable clients={clients} openClient={openClient} />
        </>
      )}
    </>
  );
}
