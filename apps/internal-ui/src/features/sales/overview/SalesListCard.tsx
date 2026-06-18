import { Icon } from "../../../shared/icons";
import type { SalesListItem } from "./types";

export function SalesListCard({ title, icon, items }: { title: string; icon: "warning" | "box"; items: SalesListItem[] }) {
  return (
    <section className="sales-list-card">
      <div className="sales-list-head">
        <Icon name={icon} size={17} />
        <h3>{title}</h3>
      </div>
      {items.map((item) => (
        <a href="#" onClick={(event) => event.preventDefault()} key={item.title}>
          <span style={{ background: item.dot }} />
          <strong>{item.title}<small>{item.meta}</small></strong>
          <em>{item.time}</em>
        </a>
      ))}
    </section>
  );
}
