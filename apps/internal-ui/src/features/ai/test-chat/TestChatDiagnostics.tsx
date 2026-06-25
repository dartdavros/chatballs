import { Icon } from "../../../shared/icons";
import { diagnosticChunks } from "./model";

export function TestChatDiagnostics() {
  return (
    <section className="test-diagnostics">
      <div className="test-diagnostics-head">
        <h3>Диагностика</h3>
        <span>Последний ответ AI</span>
      </div>
      <div className="test-diagnostics-scroll">
        <div className="test-cost-grid">
          <div><span>Tokens</span><strong>1 284</strong><small>in 940 · out 344</small></div>
          <div><span>Cost</span><strong>₽0,42</strong><small>latency 3,1с</small></div>
        </div>

        <PanelTitle>ИСПОЛЬЗОВАННЫЕ ФРАГМЕНТЫ</PanelTitle>
        <div className="test-diagnostic-list">
          {diagnosticChunks.map((chunk) => (
            <div className="test-chunk" key={chunk.source}>
              <div><strong>{chunk.source}</strong><b>{chunk.score}</b></div>
              <p>{chunk.text}</p>
            </div>
          ))}
        </div>

        <PanelTitle>ВЫЗВАННЫЕ ИНСТРУМЕНТЫ</PanelTitle>
        <div className="test-diagnostic-list">
          <ToolCall name="get_offers" meta="product=firepage → 2 предложения" time="120мс" />
          <ToolCall name="create_checkout" meta="offer=OFR-FP-BOX · ₽4 900 (симуляция)" time="88мс" />
        </div>

        <PanelTitle>ПЕРЕДАЧА ОПЕРАТОРУ</PanelTitle>
        <div className="test-handoff"><Icon name="check" size={16} />Передачи оператору не было — сценарий в рамках агента.</div>
      </div>
    </section>
  );
}

function PanelTitle({ children }: { children: string }) {
  return <div className="test-panel-title">{children}</div>;
}

function ToolCall({ meta, name, time }: { meta: string; name: string; time: string }) {
  return (
    <div className="test-tool-call">
      <Icon name="check" size={15} />
      <div><strong>{name}</strong><span>{meta}</span></div>
      <small>{time}</small>
    </div>
  );
}
