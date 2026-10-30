import { t } from "../../../i18n";
import { Icon } from "../../../shared/icons";
import { StatusPill } from "../../../shared/ui";
import { adapterOf, connectionBadge, scenariosLabel } from "./model";
import { ServiceLogo } from "./ServiceLogo";
import type { ServiceAdapter, ServiceConnection } from "./types";

/** Подключения сервисов организации (кадр «Список»): строка открывает карточку. */
export function ServiceConnectionsTable({ adapters, connections, onOpen }: {
  adapters: ServiceAdapter[];
  connections: ServiceConnection[];
  onOpen: (connection: ServiceConnection) => void;
}) {
  return (
    <div className="table-card service-connections">
      <div className="service-connections-row is-head">
        <span>{t("services.col_connection")}</span><span>{t("services.col_service")}</span>
        <span>{t("services.col_scenarios")}</span><span>{t("services.col_state")}</span><span />
      </div>
      {connections.map((connection) => {
        const adapter = adapterOf(adapters, connection);
        const badge = connectionBadge(connection);
        return (
          <button className="service-connections-row" type="button" key={connection.id} onClick={() => onOpen(connection)}>
            <span className="service-connections-name"><strong>{connection.name}</strong><small>{connection.host}</small></span>
            <span>{adapter && <ServiceLogo adapter={adapter} height={16} />}</span>
            <span className="service-connections-scenarios">{scenariosLabel(connection)}</span>
            <span><StatusPill status={badge.status} label={badge.label} /></span>
            <span className="service-connections-chevron"><Icon name="chevronRight" size={16} strokeWidth={2} /></span>
          </button>
        );
      })}
    </div>
  );
}
