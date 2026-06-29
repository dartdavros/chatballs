import { Icon } from "../../../shared/icons";
import { dailyBudget, type AiAgentDetail } from "./model";

export function AiAgentOverviewTab({ agent, toggleActive }: { agent: AiAgentDetail; toggleActive: () => void }) {
  return (
    <div className="ai-agent-overview">
      <div className="ai-agent-overview-main">
        <section className="ai-card">
          <h3>Назначение агента</h3>
          <p className="ai-agent-purpose">—</p>
        </section>
        <section className="ai-card">
          <h3>Runtime сейчас</h3>
          <div className="ai-runtime-grid">
            <div><span>Активные диалоги</span><strong>—</strong></div>
            <div><span>В очереди на ответ</span><strong>—</strong></div>
            <div><span>Ср. время ответа</span><strong>—</strong></div>
          </div>
        </section>
      </div>
      <div className="ai-agent-overview-side">
        <section className="ai-card">
          <h3>Лимиты</h3>
          <div className="ai-limit-row"><span>Диалогов в день</span><b>—</b></div>
          <div className="ai-limit-bar"><i style={{ width: "0%" }} /></div>
          <div className="ai-limit-row"><span>Бюджет в день</span><b>{dailyBudget(agent.limits)}</b></div>
          <div className="ai-limit-bar"><i style={{ width: "0%" }} /></div>
        </section>
        <section className="ai-card">
          <h3>Управление</h3>
          <button type="button" className="ai-manage-btn" disabled><Icon name="edit" size={16} />Изменить лимиты</button>
          <button type="button" className="ai-manage-btn warning" onClick={toggleActive}>
            <Icon name={agent.isActive ? "pause" : "bolt"} size={16} />
            {agent.isActive ? "Остановить агента" : "Запустить агента"}
          </button>
        </section>
      </div>
    </div>
  );
}
