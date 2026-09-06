import { Icon } from "../../../shared/icons";

// Пустой список (кадр S1, §5.2): что это, зачем и что нажать.
export function SalesClientsEmpty({ onOpenIntegrations }: { onOpenIntegrations: () => void }) {
  return (
    <div className="sales-clients-blank">
      <span><Icon name="user" size={22} /></span>
      <div>
        <strong>Контакты появятся, когда клиенты напишут вашему агенту</strong>
        <p>Каждый, кто написал через Telegram, MAX, почту или виджет, становится контактом с историей диалогов.</p>
      </div>
      <button type="button" onClick={onOpenIntegrations}>Настроить подключения</button>
    </div>
  );
}
