import { productAccent } from "../../../shared/utils";
import { channelDescription, channelMark, type ChannelOption } from "./model";
import { CreateAgentStepCard } from "./CreateAgentStepCard";

export function ProductChoiceStep({ channels, selectedChannelCode, channelsWithAgents, onSelect }: { channels: ChannelOption[]; selectedChannelCode: string | null; channelsWithAgents: string[]; onSelect: (channelCode: string) => void }) {
  return (
    <CreateAgentStepCard number={1} title="Канал обработки" text="Доступны только каналы без агента. У канала может быть не более одного агента.">
      <div className="ai-create-product-list">
        {channels.map((channel) => {
          const selected = selectedChannelCode === channel.code;
          const accent = productAccent(channel.code);
          return (
            <button className={selected ? "is-selected" : ""} type="button" onClick={() => onSelect(channel.code)} key={channel.code}>
              <span className="ai-create-product-mark" style={{ background: accent.bg, color: accent.color }}>{channelMark(channel)}</span>
              <span><strong>{channel.name}</strong><small>{channelDescription(channel)}</small></span>
              <i />
            </button>
          );
        })}
      </div>
      {channelsWithAgents.length > 0 && (
        <div className="ai-create-note">
          У каналов <b>{channelsWithAgents.join(", ")}</b> агент уже есть — для них доступен переход в существующую карточку, а не создание второго.
        </div>
      )}
    </CreateAgentStepCard>
  );
}
