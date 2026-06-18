import { Icon } from "../../../shared/icons";
import type { salesClientDetail } from "./model";

type Identity = typeof salesClientDetail.identities[number];

export function SalesClientIdentitiesTab({ identities }: { identities: Identity[] }) {
  return (
    <div className="sales-client-list-card">
      {identities.map((identity) => (
        <div className="sales-client-identity-row" key={identity.name}>
          <span className="sales-client-identity-icon" style={{ background: identity.bg ?? "#f5f5f5", color: "#8c8c8c" }}>
            {identity.icon ? <Icon name={identity.icon} size={15} /> : <i style={{ background: identity.color }} />}
          </span>
          <span><strong>{identity.name}</strong><small className={identity.icon === "phone" ? "muted" : ""}>{identity.value}</small></span>
          <b className={identity.ok ? "ok" : ""}>{identity.status}</b>
          <button type="button">Исправить</button>
        </div>
      ))}
    </div>
  );
}
