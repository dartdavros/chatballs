import type { Employee } from "../../types";
import { auditItem, formatDate, formatLastLogin, roleBadge, statusBadge } from "./model";
import { t } from "../../i18n";

// Правая колонка карточки (кадры E3/E4): учётная запись и аудит.

export function EmployeeDetailRail({ employee }: { employee: Employee }) {
  const audit = (employee.auditEvents ?? []).map(auditItem);
  const account = [
    { label: t("common.status"), value: statusBadge(employee).text },
    { label: t("common.role"), value: roleBadge(employee.role).text },
    { label: t("admin.created"), value: formatDate(employee.createdAt) },
    { label: t("admin.last_sign"), value: formatLastLogin(employee.lastLogin) },
  ];

  return (
    <aside className="employee-rail">
      <section className="employee-card is-rail">
        <h3>{t("admin.account")}</h3>
        {account.map((row) => (
          <div className="employee-account-row" key={row.label}>
            <small>{row.label}</small>
            <span>{row.value}</span>
          </div>
        ))}
      </section>
      <section className="employee-card is-rail">
        <h3>{t("common.audit")}</h3>
        {audit.map((item, index) => (
          <div className="employee-audit-row" key={`${item.code}-${index}`}>
            <i style={{ background: item.dot }} />
            <div>
              <strong>{item.text}</strong>
              <small>{item.code} · {item.time}</small>
            </div>
          </div>
        ))}
        {audit.length === 0 && <p className="employee-create-note">{t("admin.no_events_yet_2")}</p>}
      </section>
    </aside>
  );
}
