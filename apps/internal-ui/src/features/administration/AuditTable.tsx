import { formatDate } from "../../shared/utils";
import type { AuditEvent } from "./model";

function formatTime(value: string): string {
  return new Intl.DateTimeFormat("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function AuditTable({ events }: { events: AuditEvent[] }) {
  if (events.length === 0) {
    return (
      <div className="administration-card">
        <div className="empty-state"><strong>Событий пока нет</strong></div>
      </div>
    );
  }

  return (
    <div className="administration-card administration-audit">
      <table className="baseline-table">
        <thead>
          <tr>
            <th>Дата</th>
            <th>Сотрудник</th>
            <th>Действие</th>
            <th>Результат</th>
          </tr>
        </thead>
        <tbody>
          {events.map((event) => (
            <tr key={event.id}>
              <td>
                <span>{formatDate(event.createdAt)}</span>
                <small>{formatTime(event.createdAt)}</small>
              </td>
              <td>{event.actor}</td>
              <td>{event.action}</td>
              <td>
                <span className={`administration-audit-result is-${event.result.toLowerCase()}`}>
                  {event.resultLabel}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
