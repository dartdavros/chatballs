import { EVENT_TYPE_LABEL, dateTimeLong, type ApiSaleEvent } from "../registry/model";

const SOURCE_LABEL: Record<ApiSaleEvent["sourceType"], string> = {
  PRODUCT_API: "Product API",
  MANUAL: "Ручная",
  LEGACY_IMPORT: "Legacy import",
};

const STATUS_TONE: Record<ApiSaleEvent["processingStatus"], string> = {
  APPLIED: "done",
  RECEIVED: "active",
  RETRYABLE: "active",
  REJECTED: "error",
};

// Append-only журнал событий продажи (SPEC-HUB-0014 §8.2). Только чтение.
export function SaleEventTimeline({ events }: { events: ApiSaleEvent[] }) {
  if (events.length === 0) return <p className="sale-timeline-empty">Событий пока нет.</p>;
  return (
    <div className="sale-timeline">
      {events.map((event) => (
        <div className="sale-timeline-item" key={event.id}>
          <div className={`sale-timeline-dot ${STATUS_TONE[event.processingStatus]}`} />
          <div className="sale-timeline-body">
            <div className="sale-timeline-head">
              <strong>{EVENT_TYPE_LABEL[event.eventType] ?? event.eventType}</strong>
              <span className="sale-timeline-source">{SOURCE_LABEL[event.sourceType]}</span>
            </div>
            <div className="sale-timeline-meta">
              <span>{dateTimeLong(event.occurredAt)}</span>
              {event.actor && <span>· {event.actor.name}</span>}
              {event.processingStatus !== "APPLIED" && <span className="sale-timeline-warn">· {event.processingStatus}</span>}
            </div>
            {event.processingError && <div className="sale-timeline-error">{event.processingError}</div>}
          </div>
        </div>
      ))}
    </div>
  );
}
