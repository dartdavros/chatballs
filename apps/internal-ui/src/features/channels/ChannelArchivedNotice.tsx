import { StatusPill } from "../../shared/ui";

/** Архивный канал: что это значит и как вернуть в работу. */
export function ChannelArchivedNotice({ name, code }: { name: string; code: string }) {
  return (
    <section className="channel-archived-state">
      <div className="channel-section-eyebrow">АРХИВНЫЙ КАНАЛ</div>
      <div className="channel-archived-summary">
        <div><strong>{name}</strong><code>{code}</code></div>
        <StatusPill status="archived" />
      </div>
      <p>Не принимает новые диалоги и недоступен для выбора в настройках подключений. История диалогов сохранена и доступна.</p>
    </section>
  );
}
