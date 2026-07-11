import { Icon } from "../../../shared/icons";
import type { CommandVm } from "./model";
import { RailCard } from "./RailCard";

export function CommandRail({ vm }: { vm: CommandVm }) {
  return (
    <aside className="command-rail">
      <RailCard title="Требует внимания" icon="warning" iconColor="#faad14" count={String(vm.attention.length)}>
        {vm.attention.length === 0 && <div className="attention-empty">Нет событий, требующих внимания</div>}
        {vm.attention.map((item) => (
          <a className="attention-row" href="#" onClick={(event) => event.preventDefault()} key={item.title}>
            <span style={{ background: item.dot }} />
            <span><strong>{item.title}</strong><small>{item.meta}</small></span>
            <em>{item.time}</em>
          </a>
        ))}
      </RailCard>
      <RailCard title="Состояние интеграций" icon="plug" iconColor="#595959" side={<span style={{ color: vm.intHeadColor }}>{vm.okCount}</span>}>
        {vm.integrations.map((item) => (
          <div className="integration-row" key={item.name}>
            <span style={{ background: item.dot }} />
            <span><strong>{item.name}</strong><small>{item.group}</small></span>
            <em style={{ color: item.statusColor }}>{item.statusLabel}</em>
          </div>
        ))}
      </RailCard>
      <section className="ai-spend-card">
        <div className="rail-card-head">
          <div><Icon name="bolt" size={17} /><strong>Расходы AI</strong></div>
          <span>{vm.periodLabel}</span>
        </div>
        <div className="ai-spend-main"><strong>{vm.aiSpendStr}</strong>{vm.hasBudget && <span>из {vm.budgetStr}</span>}</div>
        {vm.hasBudget ? (
          <>
            <div className="ai-progress"><span style={{ width: `${vm.aiPct}%`, background: vm.aiBarColor }} /></div>
            <p>{vm.aiPct}% дневного бюджета</p>
          </>
        ) : (
          <p>Дневной лимит не задан</p>
        )}
        <div className="ai-grid">
          <SmallAiMetric label="Токены" value={vm.aiTokens} />
          <SmallAiMetric label="Диалоги" value={vm.aiDialogs} />
          <SmallAiMetric label="Цена диалога" value={vm.costPerDialog} />
        </div>
      </section>
    </aside>
  );
}

function SmallAiMetric({ label, value }: { label: string; value: string }) {
  return <div><span>{label}</span><strong>{value}</strong></div>;
}
