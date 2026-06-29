import { Icon } from "../../../shared/icons";
import { testChannels, testScenarios, type TestChannel } from "./model";

export function TestChatSidebar({
  channel,
  scenario,
  setChannel,
  setScenario,
}: {
  channel: TestChannel;
  scenario: string;
  setChannel: (channel: TestChannel) => void;
  setScenario: (scenario: string) => void;
}) {
  return (
    <section className="test-chat-sidebar">
      <div className="test-chat-sidebar-scroll">
        <div className="test-chat-label">ЧЕРНОВИК ВЕРСИИ</div>
        <label className="test-release-select">
          <select defaultValue="REL-FP-v5">
            <option value="REL-FP-v5">REL-FP-v5 · Черновик версии</option>
            <option value="REL-FP-v4">REL-FP-v4 · Опубликована</option>
          </select>
          <Icon name="chevron" size={15} />
        </label>
        <div className="test-agent-chip">
          <Icon name="robot" size={15} />
          <span>FirePage Sales · gpt-4o-mini · temp 0.4</span>
        </div>

        <div className="test-chat-label">КАНАЛ СИМУЛЯЦИИ</div>
        <div className="test-channel-row">
          {testChannels.map((item) => (
            <button className={channel === item.key ? "active" : ""} type="button" onClick={() => setChannel(item.key)} key={item.key}>
              <span style={{ background: item.dot }} />
              {item.label}
            </button>
          ))}
        </div>

        <div className="test-chat-label">ГОТОВЫЕ СЦЕНАРИИ</div>
        <div className="test-scenarios">
          {testScenarios.map((item) => (
            <button className={scenario === item.id ? "active" : ""} type="button" onClick={() => setScenario(item.id)} key={item.id}>
              <strong>{item.title}</strong>
              <span>{item.desc}</span>
            </button>
          ))}
        </div>
      </div>
      <div className="test-chat-sidebar-footer">
        <button type="button"><Icon name="trash" size={15} />Очистить тестовую сессию</button>
      </div>
    </section>
  );
}
