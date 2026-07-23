import { KeyValue } from "../../shared/form-controls";
import { Icon } from "../../shared/icons";

export function ChannelWizardSummary({
  name,
  code,
  departmentName,
  productName,
  showDestinations = false,
  openAgentCreate,
  openIntegrations,
}: {
  name: string;
  code: string;
  departmentName: string;
  productName: string;
  showDestinations?: boolean;
  openAgentCreate: () => void;
  openIntegrations: () => void;
}) {
  return (
    <aside className="channel-wizard-aside">
      <div className="channel-card-aside">
        <h4>Сводка канала</h4>
        <KeyValue label="Название" value={name || "—"} />
        <KeyValue label="Код" value={code ? <code>{code}</code> : "—"} />
        <KeyValue label="Отдел" value={departmentName} />
        <KeyValue label="Продукт" value={productName} />
      </div>

      {showDestinations && (
        <>
          <DestinationCard
            tone="ai"
            title="Нужен AI-агент?"
            text="Создайте его отдельным действием в разделе AI и выберите этот канал."
            action="Перейти в раздел AI"
            onClick={openAgentCreate}
          />
          <DestinationCard
            tone="integration"
            title="Нужно подключение?"
            text="Создайте или измените подключение в разделе «Интеграции» и выберите этот канал."
            action="Перейти в интеграции"
            onClick={openIntegrations}
          />
        </>
      )}
    </aside>
  );
}

function DestinationCard({
  tone,
  title,
  text,
  action,
  onClick,
}: {
  tone: "ai" | "integration";
  title: string;
  text: string;
  action: string;
  onClick: () => void;
}) {
  return (
    <section className={`channel-wizard-destination is-${tone}`}>
      <p><b>{title}</b> {text}</p>
      <button className="link has-icon" type="button" onClick={onClick}>
        {action}
        <Icon name="arrow" size={14} />
      </button>
    </section>
  );
}
