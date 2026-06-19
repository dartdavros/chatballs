import { Button } from "../../../shared/ui-controls";
import type { RouteKey } from "../../../types";
import type { salesClientDetail } from "./model";

type Client = typeof salesClientDetail;

export function SalesClientOverviewTab({ client, setRoute }: { client: Client; setRoute: (route: RouteKey) => void }) {
  return (
    <div className="sales-client-overview">
      <div className="sales-client-overview-main">
        <SummaryGrid client={client} />
        <NeedNote note={client.note} />
        <ActivityList activity={client.activity} />
      </div>
      <div className="sales-client-overview-rail">
        <CurrentDialog setRoute={setRoute} />
        <RelatedProducts />
      </div>
    </div>
  );
}

function SummaryGrid({ client }: { client: Client }) {
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

function NeedNote({ note }: { note: string }) {
  const [beforeProduct, afterProduct] = note.split("Foxray Team");
  return (
    <section className="sales-client-section-card">
      <div className="sales-client-section-head"><h3>Потребность и заметка</h3><button type="button">Изменить</button></div>
      <div className="sales-client-note">{beforeProduct}<b>Foxray Team</b>{afterProduct}</div>
    </section>
  );
}

function ActivityList({ activity }: { activity: Client["activity"] }) {
  return (
    <section className="sales-client-section-card">
      <h3>Последняя активность</h3>
      <div className="sales-client-timeline">
        {activity.map((item, index) => <TimelineItem item={item} last={index === activity.length - 1} key={`${item.title}-${item.time}`} />)}
      </div>
    </section>
  );
}

function TimelineItem({ item, last }: { item: Client["activity"][number]; last: boolean }) {
  return (
    <div className="sales-client-timeline-row">
      <div className="sales-client-timeline-mark"><span style={{ background: item.color }} />{!last && <i />}</div>
      <div className="sales-client-timeline-text">
        <div>{item.title} {item.code && <b>{item.code}</b>} {item.suffix}</div>
        <time>{item.time}</time>
      </div>
    </div>
  );
}

function CurrentDialog({ setRoute }: { setRoute: (route: RouteKey) => void }) {
  return (
    <section className="sales-client-section-card">
      <div className="sales-client-section-head">
        <h3>Текущий диалог</h3>
        <span className="sales-client-status-blue"><i />Оператор</span>
      </div>
      <p className="sales-client-current-dialog">Foxray · Web Chat · ведёт <b>Иван Петров</b>.<br />«Помогу с настройкой рабочих мест.»</p>
      <Button className="sales-client-outline-action" variant="secondary" onClick={() => setRoute("salesDialogs")}>Открыть диалог</Button>
    </section>
  );
}

function RelatedProducts() {
  return (
    <section className="sales-client-section-card">
      <h3>Связанные продукты</h3>
      <div className="sales-client-related-row"><span><i style={{ background: "#722ed1" }} />Foxray</span><b>Team · активна</b></div>
      <div className="sales-client-related-row"><span><i style={{ background: "#1677ff" }} />FirePage</span><b>Pro · разовая</b></div>
    </section>
  );
}
