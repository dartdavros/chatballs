import { Fragment, useState } from "react";

import { Icon } from "../../shared/icons";
import { shortDate, shortDateYear } from "../../shared/utils";
import type { AuditEvent } from "./model";
import { t } from "../../i18n";

// Журнал действий. Три вещи, без которых он был нечитаем:
// * день отбивается заголовком — иначе сотни строк идут сплошняком;
// * у действия есть подпись, раздел и объект, а не одна строка на всё;
// * строка раскрывается: IP, correlation id и payload события. Раньше эти поля
//   были в базе, но наружу не отдавались, и разобраться в событии было нечем.

function formatTime(value: string): string {
  return new Intl.DateTimeFormat("ru-RU", { hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

function dayKey(value: string): string {
  const date = new Date(value);
  return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;
}

/** «Сегодня» · «Вчера» · «5 сен» · «5 сен 2025» — заголовок дня. Год только у
 *  прошлых лет: в заголовке он лишний шум, а журнал почти всегда свежий. */
function dayLabel(value: string): string {
  const date = new Date(value);
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);
  if (dayKey(value) === dayKey(today.toISOString())) return t("common.today");
  if (dayKey(value) === dayKey(yesterday.toISOString())) return t("admin.yesterday");
  return date.getFullYear() === today.getFullYear() ? shortDate(date) : shortDateYear(date);
}

function detailLines(event: AuditEvent): Array<[string, string]> {
  const lines: Array<[string, string]> = [];
  if (event.actorEmail) lines.push([t("common.operator"), `${event.actor} · ${event.actorEmail}`]);
  lines.push([t("admin.action_code"), event.action]);
  if (event.objectType) lines.push([t("common.object"), `${event.objectType}${event.objectId ? ` · ${event.objectId}` : ""}`]);
  if (event.sourceIp) lines.push(["IP", event.sourceIp]);
  if (event.correlationId) lines.push(["Correlation id", event.correlationId]);
  Object.entries(event.details ?? {}).forEach(([key, value]) => {
    lines.push([key, typeof value === "object" && value !== null ? JSON.stringify(value) : String(value)]);
  });
  return lines;
}

export function AuditTable({ events }: { events: AuditEvent[] }) {
  const [openId, setOpenId] = useState<number | null>(null);
  let lastDay = "";

  return (
    <div className="table-card audit-card">
      <table className="baseline-table audit-table">
        <thead>
          <tr>
            <th className="audit-col-time">{t("admin.time")}</th>
            <th className="audit-col-actor">{t("common.operator")}</th>
            <th>{t("common.action")}</th>
            <th className="audit-col-object">{t("common.object")}</th>
            <th className="audit-col-result">{t("admin.result")}</th>
            <th className="audit-col-toggle" />
          </tr>
        </thead>
        <tbody>
          {events.map((event) => {
            const day = dayKey(event.createdAt);
            const newDay = day !== lastDay;
            lastDay = day;
            const open = openId === event.id;
            return (
              <Fragment key={event.id}>
                {newDay && (
                  <tr className="audit-day">
                    <td colSpan={6}>{dayLabel(event.createdAt)}</td>
                  </tr>
                )}
                <tr
                  className={`audit-row ${open ? "is-open" : ""}`}
                  onClick={() => setOpenId(open ? null : event.id)}
                >
                  <td className="audit-col-time">{formatTime(event.createdAt)}</td>
                  <td className="audit-col-actor">
                    <span>{event.actor}</span>
                  </td>
                  <td>
                    {/* Подписи может не быть — тогда показываем код действия,
                        а не заглушку: по коду видно, что произошло. */}
                    {event.actionLabel
                      ? <strong>{event.actionLabel}</strong>
                      : <code className="audit-action-code">{event.action}</code>}
                    <small>{event.categoryLabel}</small>
                  </td>
                  <td className="audit-col-object">{event.object || "—"}</td>
                  <td className="audit-col-result">
                    <span className={`audit-result is-${event.result.toLowerCase()}`}>{event.resultLabel}</span>
                  </td>
                  <td className="audit-col-toggle">
                    <span className="audit-toggle" aria-hidden="true">
                      <Icon name="chevron" size={14} strokeWidth={2.2} />
                    </span>
                  </td>
                </tr>
                {open && (
                  <tr className="audit-details">
                    <td colSpan={6}>
                      <dl>
                        {detailLines(event).map(([label, value]) => (
                          <div key={label}>
                            <dt>{label}</dt>
                            <dd>{value}</dd>
                          </div>
                        ))}
                      </dl>
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
