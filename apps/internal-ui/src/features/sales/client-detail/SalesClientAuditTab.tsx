import { EmptyState } from "../../../shared/ui";
import type { ClientDetailVm } from "./model";
import { t } from "../../../i18n";

export function SalesClientAuditTab({ audit }: { audit: ClientDetailVm["audit"] }) {
  if (audit.length === 0) return <EmptyState title={t("sales.no_events_yet")} />;
  return (
    <div className="sales-client-table-card">
      <table className="sales-client-detail-table">
        <thead>
          <tr>
            <th>{t("admin.time")}</th>
            <th>{t("common.action")}</th>
            <th>{t("common.object")}</th>
            <th>{t("common.operator")}</th>
            <th>{t("admin.result")}</th>
          </tr>
        </thead>
        <tbody>
          {audit.map((item, index) => (
            <tr key={`${item.time}-${item.action}-${index}`}>
              <td>{item.time}</td>
              <td>{item.action}</td>
              <td>{item.object}</td>
              <td>{item.actor}</td>
              <td>{item.result}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
