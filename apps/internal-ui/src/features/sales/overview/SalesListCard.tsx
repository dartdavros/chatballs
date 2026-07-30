import type { SalesListItem } from "./types";

export function SalesListCard({ title, items, openConversation }: { title: string; items: SalesListItem[]; openConversation: (conversationId: number) => void }) {
  return (
    <section className="sales-panel-card problem-dialogs-card">
      <h3>{title}</h3>
      {items.length === 0 && <div className="attention-empty">Нет проблемных диалогов</div>}
      <div className="problem-dialogs-list">
        {items.map((item) => (
          <button className="attention-row" type="button" key={`${item.title}-${item.time}`} onClick={() => item.conversationId && openConversation(item.conversationId)}>
            <span style={{ background: item.dot }} />
            <span><strong>{item.title}</strong><small>{item.meta}</small></span>
            <em>{item.time}</em>
          </button>
        ))}
      </div>
    </section>
  );
}
