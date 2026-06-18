import { SalesClientsFilters } from "./clients/SalesClientsFilters";
import { SalesClientsHeader } from "./clients/SalesClientsHeader";
import { SalesClientsTable } from "./clients/SalesClientsTable";
import { useSalesClients } from "./clients/useSalesClients";

export function SalesClientsPage() {
  const clients = useSalesClients();

  return (
    <>
      <SalesClientsHeader shownCount={clients.rows.length} />
      <SalesClientsFilters clients={clients} />
      <SalesClientsTable clients={clients} />
    </>
  );
}
