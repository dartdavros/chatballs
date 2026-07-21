import { MetricBox } from "../../shared/form-controls";
import { Icon } from "../../shared/icons";
import type { Channel } from "./types";

export function ChannelCountersSection({ channel, canOpenDialogs, openDialogs }: { channel: Channel; canOpenDialogs: boolean; openDialogs: () => void }) {
  return (
    <section className="channel-card-section">
      <header>
        <h3>Счётчики</h3>
        {canOpenDialogs && (
          <button className="link has-icon" type="button" onClick={openDialogs}>
            Открыть диалоги канала
            <Icon name="arrow" size={14} />
          </button>
        )}
      </header>
      <div className="channel-counters">
        <MetricBox label="ОТКРЫТЫЕ ДИАЛОГИ" value={channel.counters.openConversations} />
        <MetricBox label="ПОДКЛЮЧЕНИЯ" value={channel.counters.connections} />
      </div>
    </section>
  );
}
