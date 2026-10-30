import { useState } from "react";

import { t } from "../../../i18n";
import { EmptyState, LoadingState } from "../../../shared/ui";
import { ServiceConnectModal } from "./connect/ServiceConnectModal";
import { markConnected } from "./connectedNotice";
import { ServiceCatalog } from "./ServiceCatalog";
import { ServiceConnectionsTable } from "./ServiceConnectionsTable";
import type { ServiceAdapter } from "./types";
import { useServices } from "./useServices";
import "./services.css";

/** Вкладка «Сервисы» раздела «Интеграции» (кадры «Список» и «Первое подключение»). */
export function ServicesTab({ openConnection }: { openConnection: (id: number) => void }) {
  const services = useServices();
  const [connecting, setConnecting] = useState<ServiceAdapter | null>(null);

  if (services.loading) return <LoadingState />;
  if (services.failed) return <EmptyState title={t("services.load_failed")} />;

  return (
    <div className="services-tab">
      {services.connections.length > 0 && (
        <ServiceConnectionsTable adapters={services.adapters} connections={services.connections} onOpen={(item) => openConnection(item.id)} />
      )}
      <ServiceCatalog adapters={services.adapters} connections={services.connections} onConnect={setConnecting} />
      {connecting && (
        <ServiceConnectModal adapter={connecting} mode={{ kind: "new" }} onClose={() => setConnecting(null)}
          onDone={(id) => { markConnected(id); setConnecting(null); openConnection(id); }} />
      )}
    </div>
  );
}
