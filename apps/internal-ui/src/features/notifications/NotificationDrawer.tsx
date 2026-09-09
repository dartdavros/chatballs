import { Drawer } from "antd";

import { Icon } from "../../shared/icons";
import { LEVEL_META, type AppNotification } from "./model";
import { t } from "../../i18n";

function group(items: AppNotification[]): { today: AppNotification[]; earlier: AppNotification[] } {
  const now = new Date();
  const isToday = (iso: string) => {
    const d = new Date(iso);
    return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate();
  };
  return {
    today: items.filter((n) => isToday(n.createdAt)),
    earlier: items.filter((n) => !isToday(n.createdAt)),
  };
}

function fmt(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const today = d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate();
  return today
    ? d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })
    : d.toLocaleDateString("ru-RU", { day: "2-digit", month: "short" });
}

export function NotificationDrawer({ open, items, unreadCount, onClose, onItemClick, onMarkAll }: {
  open: boolean;
  items: AppNotification[];
  unreadCount: number;
  onClose: () => void;
  onItemClick: (n: AppNotification) => void;
  onMarkAll: () => void;
}) {
  const { today, earlier } = group(items);
  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={t("admin.notifications")}
      width={400}
      extra={unreadCount > 0 ? <button className="notif-mark-all" type="button" onClick={onMarkAll}>{t("admin.mark_all_as_read")}</button> : null}
    >
      {items.length === 0 && <div className="notif-empty">{t("admin.no_notifications")}</div>}
      {today.length > 0 && <Section title={t("common.today")} items={today} onItemClick={onItemClick} />}
      {earlier.length > 0 && <Section title={t("admin.earlier")} items={earlier} onItemClick={onItemClick} />}
    </Drawer>
  );
}

function Section({ title, items, onItemClick }: { title: string; items: AppNotification[]; onItemClick: (n: AppNotification) => void }) {
  return (
    <div className="notif-section">
      <div className="notif-section-title">{title}</div>
      {items.map((n) => {
        const meta = LEVEL_META[n.level] ?? LEVEL_META.INFO;
        return (
          <button className={`notif-item ${n.unread ? "unread" : ""}`} type="button" key={n.id} onClick={() => onItemClick(n)}>
            <span className="notif-item-icon" style={{ background: `${meta.color}1a`, color: meta.color }}><Icon name={meta.icon} size={16} /></span>
            <span className="notif-item-body">
              <span className="notif-item-title">{n.title}</span>
              {n.body && <span className="notif-item-text">{n.body}</span>}
              <span className="notif-item-time">{fmt(n.createdAt)}</span>
            </span>
            {n.unread && <i className="notif-item-dot" />}
          </button>
        );
      })}
    </div>
  );
}
