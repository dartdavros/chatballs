import { EmptyState } from "../../../shared/ui";
import type { ClientDetailVm } from "./model";

export function SalesClientIdentitiesTab({ identities }: { identities: ClientDetailVm["identities"] }) {
  if (identities.length === 0) return <EmptyState title="Нет идентификаторов каналов" />;
  return (
    <div className="sales-client-list-card">
      {identities.map((identity) => (
        <div className="sales-client-identity-row" key={`${identity.name}-${identity.value}`}>
          <span className="sales-client-identity-icon" style={{ background: identity.bg, color: "#8c8c8c" }}>
            <i style={{ background: identity.color }} />
          </span>
          <span><strong>{identity.name}</strong><small>{identity.value}</small></span>
          <b className={identity.ok ? "ok" : ""}>{identity.status}</b>
        </div>
      ))}
    </div>
  );
}
