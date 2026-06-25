import { Icon } from "../../../shared/icons";
import { StatusPill } from "../../../shared/ui";
import { Button } from "../../../shared/ui-controls";
import { productAccent } from "../../../shared/utils";
import type { RouteKey } from "../../../types";
import { dailyBudget, publishedRelease, releaseDisplayName, type AiAgentDetail, type AiReleaseFull } from "./model";

export function AiAgentDetailHeader({
  agent,
  releases,
  setRoute,
  openRelease,
  createRelease,
}: {
  agent: AiAgentDetail;
  releases: AiReleaseFull[];
  setRoute: (route: RouteKey) => void;
  openRelease: (releaseId: number) => void;
  createRelease: () => void;
}) {
  const accent = productAccent(agent.product.code);
  const release = publishedRelease(releases);
  return (
    <section className="ai-agent-header">
      <div className="ai-agent-heading">
        <span className="ai-agent-icon" style={{ background: accent.bg, color: accent.color }}><Icon name="robot" size={27} /></span>
        <div className="ai-agent-title">
          <div className="ai-agent-title-row">
            <h1>{agent.name}</h1>
            <StatusPill status={agent.isActive ? "active" : "disabled"} />
          </div>
          <div className="ai-agent-meta">
            <div><span>Продукт</span><button type="button" className="ai-agent-meta-link" onClick={() => setRoute("products")}>{agent.product.name}</button></div>
            <div><span>Модель</span><code className="ai-mono">{agent.model}</code></div>
            <div><span>Текущая версия</span>{release ? <button type="button" className="ai-agent-meta-link ai-mono" onClick={() => openRelease(release.id)}>{releaseDisplayName(release)}</button> : <b className="ai-agent-meta-empty">—</b>}</div>
            <div><span>Лимиты</span><b>{dailyBudget(agent.limits)}</b></div>
          </div>
        </div>
      </div>
      <div className="ai-agent-header-actions">
        <Button variant="secondary" icon="message" onClick={() => setRoute("aiTestChat")}>Тест-чат</Button>
        <Button variant="primary" icon="plus" onClick={createRelease}>Создать черновик версии</Button>
      </div>
    </section>
  );
}
