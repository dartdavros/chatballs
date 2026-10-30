import { t } from "../../../i18n";
import { Button } from "../../../shared/ui-controls";
import { connectionsOf } from "./model";
import { ServiceLogo } from "./ServiceLogo";
import type { ServiceAdapter, ServiceConnection } from "./types";

/** Каталог установленных адаптеров: только то, что реально стоит в этой версии. */
export function ServiceCatalog({ adapters, connections, onConnect }: {
  adapters: ServiceAdapter[];
  connections: ServiceConnection[];
  onConnect: (adapter: ServiceAdapter) => void;
}) {
  return (
    <section className="service-catalog">
      <div>
        <h3>{connections.length ? t("services.catalog_add") : t("services.catalog_first")}</h3>
        <p>{t("services.catalog_lead")}</p>
      </div>
      {adapters.length > 0 && (
        <div className="service-catalog-grid">
          {adapters.map((adapter) => {
            const count = connectionsOf(adapter, connections);
            return (
              <article className="service-catalog-card" key={adapter.key}>
                <div className="service-catalog-logo"><ServiceLogo adapter={adapter} height={22} /></div>
                <p>{adapter.about}</p>
                <div className="service-catalog-actions">
                  <Button variant="secondary" onClick={() => onConnect(adapter)}>{count ? t("services.connect_more") : t("services.connect")}</Button>
                  {count > 0 && <span>{t("services.connected_count", { count })}</span>}
                </div>
              </article>
            );
          })}
        </div>
      )}
      <p className="service-catalog-note"><strong>{t("services.not_found_title")}</strong> {t("services.not_found_text")}</p>
    </section>
  );
}
