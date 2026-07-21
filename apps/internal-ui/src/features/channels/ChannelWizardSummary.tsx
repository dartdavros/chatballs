import { KeyValue } from "../../shared/form-controls";
import { Icon } from "../../shared/icons";
import { providerLabel } from "./ChannelBadge";
import type { Channel } from "./types";

/** Правая колонка финального шага: что именно создано и что делать дальше. */
export function ChannelWizardSummary({ channel, openAgentCreate }: { channel: Channel; openAgentCreate: () => void }) {
  const connections = channel.connections.length
    ? channel.connections.map((connection) => providerLabel(connection.provider)).join(", ")
    : "нет";

  return (
    <aside className="channel-wizard-aside">
      <div className="channel-card-aside channel-wizard-ai">
        <h4>Сводка канала</h4>
        <KeyValue label="Название" value={channel.name} />
        <KeyValue label="Код" value={<code>{channel.code}</code>} />
        <KeyValue label="Отдел" value={channel.departmentName ?? "Без отдела"} />
        <KeyValue label="Продукт" value={channel.product?.name ?? "— непродуктовый"} />
        <KeyValue label="Подключения" value={connections} />
      </div>
      <div className="channel-card-aside">
        <p>
          <b>Нужен AI-агент?</b> Создайте его отдельным действием в разделе AI — он подключится
          к этому каналу.
        </p>
        <button className="link has-icon" type="button" onClick={openAgentCreate}>
          Перейти в раздел AI
          <Icon name="arrow" size={14} />
        </button>
      </div>
    </aside>
  );
}
