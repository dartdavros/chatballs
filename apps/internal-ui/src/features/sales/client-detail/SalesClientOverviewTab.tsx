import { Button } from "../../../shared/ui-controls";
import type { ClientDetailVm } from "./model";

export function SalesClientOverviewTab({ client, openConversation }: { client: ClientDetailVm; openConversation: (conversationId: number) => void }) {
  const currentDialog = client.dialogs.find((dialog) => dialog.active);
  return (
    <div className="sales-client-overview">
      <div className="sales-client-overview-main">
        <SummaryGrid client={client} />
        <ActivityList activity={client.activity} />
      </div>
      <div className="sales-client-overview-rail">
        {currentDialog && (
          <section className="sales-client-section-card">
            <div className="sales-client-section-head">
              <h3>Текущий диалог</h3>
              <span className="sales-client-status-blue"><i />{currentDialog.status}</span>
            </div>
            <p className="sales-client-current-dialog">{currentDialog.meta}<br />«{currentDialog.title}»</p>
            <Button className="sales-client-outline-action" variant="secondary" onClick={() => openConversation(currentDialog.id)}>Открыть диалог</Button>
          </section>
        )}
        <section className="sales-client-section-card">
          <h3>Связанные продукты</h3>
          {client.products.length === 0 ? (
            <div className="sales-client-related-empty">Нет привязанных продуктов</div>
          ) : (
            client.products.map((product) => (
              <div className="sales-client-related-row" key={product.name}><span><i style={{ background: product.color }} />{product.name}</span></div>
            ))
          )}
        </section>
      </div>
    </div>
  );
}

function SummaryGrid({ client }: { client: ClientDetailVm }) {
  return (
    <div className="sales-client-summary">
      {client.summary.map((item) => (
        <div key={item.label}>
          <span>{item.label}</span>
          <strong className={`${item.accent ? "accent" : ""} ${item.compact ? "compact" : ""}`}>{item.value}</strong>
        </div>
      ))}
    </div>
  );
}

function ActivityList({ activity }: { activity: ClientDetailVm["activity"] }) {
  if (activity.length === 0) {
    return <section className="sales-client-section-card"><h3>Последняя активность</h3><div className="sales-client-related-empty">Нет событий</div></section>;
  }
  return (
    <section className="sales-client-section-card">
      <h3>Последняя активность</h3>
      <div className="sales-client-timeline">
        {activity.map((item, index) => (
          <div className="sales-client-timeline-row" key={`${item.title}-${item.time}-${index}`}>
            <div className="sales-client-timeline-mark"><span style={{ background: item.color }} />{index < activity.length - 1 && <i />}</div>
            <div className="sales-client-timeline-text">
              <div>{item.title}</div>
              <time>{item.time}</time>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
