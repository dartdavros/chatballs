import type { ReactNode } from "react";
import { useState } from "react";

import type { AppData, RouteKey } from "../../types";
import { Icon } from "../../shared/icons";
import { Segmented } from "../../shared/ui";

export function CommandCenter({ data, setRoute }: { data: AppData; setRoute: (route: RouteKey) => void }) {
  const [period, setPeriod] = useState<"today" | "d7" | "d30">("today");
  const vm = commandCenterModel(period);
  return (
    <>
      <div className="command-page-header">
        <div>
          <h1>Командный центр</h1>
          <p>Состояние компании одним взглядом · обновлено только что</p>
        </div>
        <div className="command-header-actions">
          <Segmented value={period} setValue={setPeriod} items={[["today", "Сегодня"], ["d7", "7 дней"], ["d30", "30 дней"]]} />
          <button className="refresh-button"><Icon name="refresh" size={15} />Обновить</button>
        </div>
      </div>

      <section className="company-status-banner" style={{ borderLeftColor: vm.st.dot }}>
        <div className="company-status-dot" style={{ background: vm.st.bg }}><span style={{ background: vm.st.dot }} /></div>
        <div className="company-status-text">
          <strong>Компания: {vm.st.label}</strong>
          <p>{vm.compSummary}</p>
        </div>
        <div className="company-status-metrics">
          <SmallMetric label="Отделы" value="1" />
          <SmallMetric label="Открытые диалоги" value={vm.m.open} />
          <SmallMetric label={`Выручка · ${vm.periodLabel}`} value={vm.m.rev} success />
        </div>
      </section>

      <div className="command-two-column">
        <section className="command-left">
          <div className="section-head">
            <h2>Отделы</h2>
            <span>1 активный</span>
          </div>
          <article className="sales-card">
            <div className="sales-head">
              <div className="sales-icon"><Icon name="shop" size={23} /></div>
              <div className="sales-title">
                <div>
                  <h3>Продажи</h3>
                  <StatusLabel vm={vm} />
                </div>
                <p>Ответственный: Анна Котова · 4 сотрудника · 1 AI-агент</p>
              </div>
              <button className="primary-button sales-open" onClick={() => setRoute("departments")}>Открыть отдел<Icon name="arrow" size={16} /></button>
            </div>
            <div className="dept-summary">{vm.deptSummary}</div>
            <MetricGroup title="ДИАЛОГИ — СЕЙЧАС" columns={5} items={[
              { label: "Открытые диалоги", value: vm.m.open },
              { label: "Активны за 15 мин", value: vm.m.active },
              { label: "На AI", value: vm.m.ai, dot: "#722ed1" },
              { label: "На операторах", value: vm.m.op, dot: "#1677ff" },
              { label: "Ожидают оператора", value: vm.m.wait, color: vm.m.waitColor },
            ]} />
            <MetricGroup title={`КОММЕРЦИЯ — ${vm.periodLabelUpper}`} columns={4} items={[
              { label: "Незавершённые платежи", value: vm.m.pend, color: vm.m.pendColor },
              { label: "Ошибки fulfillment", value: vm.m.ferr, color: vm.m.ferrColor },
              { label: "Продажи", value: vm.m.sales },
              { label: "Чистая выручка", value: vm.m.rev, color: "#389e0d" },
            ]} />
          </article>
        </section>

        <aside className="command-rail">
          <RailCard title="Требует внимания" icon="warning" iconColor="#faad14" count={String(vm.attention.length)} action="Все">
            {vm.attention.map((item) => (
              <a className="attention-row" href="#" onClick={(event) => event.preventDefault()} key={item.title}>
                <span style={{ background: item.dot }} />
                <span><strong>{item.title}</strong><small>{item.meta}</small></span>
                <em>{item.time}</em>
              </a>
            ))}
          </RailCard>
          <RailCard title="Состояние интеграций" icon="plug" iconColor="#595959" side={<span style={{ color: vm.intHeadColor }}>{vm.okCount}/6 в норме</span>}>
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
            <div className="ai-spend-main"><strong>{vm.aiSpendStr}</strong><span>из {vm.budgetStr}</span></div>
            <div className="ai-progress"><span style={{ width: `${vm.aiPct}%`, background: vm.aiBarColor }} /></div>
            <p>{vm.aiPct}% дневного бюджета</p>
            <div className="ai-grid">
              <SmallAiMetric label="Токены" value={vm.aiTokens} />
              <SmallAiMetric label="Диалоги" value={vm.aiDialogs} />
              <SmallAiMetric label="Цена диалога" value={vm.costPerDialog} />
            </div>
          </section>
        </aside>
      </div>
      <div className="command-updated">Обновлено: сегодня, 14:32 · детерминированная сводка</div>
    </>
  );
}

type CommandVm = ReturnType<typeof commandCenterModel>;

export function commandCenterModel(period: "today" | "d7" | "d30") {
  const fmt = (n: number) => `₽${Math.round(n).toLocaleString("ru-RU").replace(/\u00a0/g, " ")}`;
  const ops = { open: 42, active: 9, ai: 35, op: 7, wait: 0, pend: 1, ferr: 0 };
  const com = {
    today: { label: "Сегодня", sales: 18, rev: 146200, aiSpend: 1240, budget: 5000, tokens: "412K", dlg: 42 },
    d7: { label: "7 дней", sales: 126, rev: 1024600, aiSpend: 8600, budget: 35000, tokens: "2,9M", dlg: 318 },
    d30: { label: "30 дней", sales: 540, rev: 4386000, aiSpend: 36400, budget: 150000, tokens: "12,4M", dlg: 1342 },
  }[period];
  const st = { label: "Нормально", color: "#389e0d", bg: "#f6ffed", border: "#b7eb8f", dot: "#52c41a" };
  const m = {
    open: String(ops.open),
    active: String(ops.active),
    ai: String(ops.ai),
    op: String(ops.op),
    wait: String(ops.wait),
    pend: String(ops.pend),
    ferr: String(ops.ferr),
    sales: String(com.sales),
    rev: fmt(com.rev),
    waitColor: "#262626",
    pendColor: "#262626",
    ferrColor: "#262626",
  };
  const attention = [
    { dot: "#faad14", title: "Незавершённый платёж · заказ ORD-10482", meta: "Продажи · Точка", time: "6 мин" },
    { dot: "#1677ff", title: "Подписка истекает через 2 дня · Foxray Pro", meta: "Продажи", time: "1 ч" },
  ];
  const integrations = [
    { name: "OpenRouter", group: "AI-провайдер", dot: "#52c41a", statusLabel: "Подключено", statusColor: "#52c41a" },
    { name: "Точка", group: "Платежи и фискализация", dot: "#52c41a", statusLabel: "Подключено", statusColor: "#52c41a" },
    { name: "MAX", group: "Канал", dot: "#52c41a", statusLabel: "Подключено", statusColor: "#52c41a" },
    { name: "Telegram", group: "Канал", dot: "#52c41a", statusLabel: "Подключено", statusColor: "#52c41a" },
    { name: "Web Chat", group: "Канал", dot: "#52c41a", statusLabel: "Подключено", statusColor: "#52c41a" },
    { name: "Fulfillment · FirePage", group: "Исполнение", dot: "#52c41a", statusLabel: "Подключено", statusColor: "#52c41a" },
  ];
  const aiPct = Math.round((com.aiSpend / com.budget) * 100);
  const aiBarColor = aiPct >= 85 ? "#ff4d4f" : aiPct >= 70 ? "#faad14" : "#1677ff";
  return {
    st,
    m,
    compSummary: "Все системы в норме. Один отдел активен, критичных событий нет.",
    deptSummary: "AI ведёт большинство диалогов. Очередь оператора пуста, незавершённых задач почти нет.",
    attention,
    integrations,
    okCount: "6",
    intHeadColor: "#389e0d",
    periodLabel: com.label,
    periodLabelUpper: com.label.toUpperCase(),
    aiSpendStr: fmt(com.aiSpend),
    budgetStr: fmt(com.budget),
    aiPct,
    aiBarColor,
    aiTokens: com.tokens,
    aiDialogs: String(com.dlg),
    costPerDialog: fmt(com.aiSpend / com.dlg),
  };
}

export function StatusLabel({ vm }: { vm: CommandVm }) {
  return (
    <span className="command-status-label" style={{ background: vm.st.bg, borderColor: vm.st.border }}>
      <span style={{ background: vm.st.dot }} />
      <em style={{ color: vm.st.color }}>{vm.st.label}</em>
    </span>
  );
}

function SmallMetric({ label, value, success = false }: { label: string; value: string; success?: boolean }) {
  return <div><span>{label}</span><strong className={success ? "success" : ""}>{value}</strong></div>;
}

function MetricGroup({ title, columns, items }: { title: string; columns: 4 | 5; items: Array<{ label: string; value: string; color?: string; dot?: string }> }) {
  return (
    <>
      <div className="metric-group-title">{title}</div>
      <div className="metric-group-grid" style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}>
        {items.map((item) => (
          <div className="metric-cell" key={item.label}>
            <div>{item.dot && <span style={{ background: item.dot }} />}{item.label}</div>
            <strong style={{ color: item.color ?? "#262626" }}>{item.value}</strong>
          </div>
        ))}
      </div>
    </>
  );
}

function RailCard({ title, icon, iconColor, count, action, side, children }: { title: string; icon: "warning" | "plug"; iconColor: string; count?: string; action?: string; side?: ReactNode; children: ReactNode }) {
  return (
    <section className="rail-card">
      <div className="rail-card-head">
        <div><span className="rail-icon" style={{ color: iconColor }}><Icon name={icon} size={17} /></span><strong>{title}</strong>{count && <b>{count}</b>}</div>
        {action && <a href="#" onClick={(event) => event.preventDefault()}>{action}</a>}
        {side}
      </div>
      <div className="rail-card-body">{children}</div>
    </section>
  );
}

function SmallAiMetric({ label, value }: { label: string; value: string }) {
  return <div><span>{label}</span><strong>{value}</strong></div>;
}

function MetricCard({ label, value, sub, compact = false }: { label: string; value: number | string; sub: string; compact?: boolean }) {
  return <article className={`metric-card ${compact ? "is-compact" : ""}`}><span>{label}</span><strong>{value}</strong><small>{sub}</small></article>;
}
