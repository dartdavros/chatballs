import { Icon } from "../../../../shared/icons";

export function ContactRow({ dot, icon, title, text, note, mono = false, muted = false }: { dot?: string; icon?: "mail" | "phone"; title: string; text: string; note?: string; mono?: boolean; muted?: boolean }) {
  return (
    <div className="sales-contact-row">
      <span>{dot && <i style={{ background: dot }} />}{icon && <Icon name={icon} size={15} />}</span>
      <div><strong className={`${mono ? "mono" : ""} ${muted ? "muted" : ""}`}>{title}</strong><small>{text}</small></div>
      {note && <em>{note}</em>}
    </div>
  );
}
