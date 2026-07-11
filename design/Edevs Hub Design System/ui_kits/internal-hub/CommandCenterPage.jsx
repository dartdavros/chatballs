const { DepartmentCard, MetricCard, IntegrationHealthCard, AttentionStatus } = window.EdevsHubDesignSystem_e4c9df;

/* Recreation of design/baseline/Командный центр.dc.html */
function CommandCenterPage({ onOpenDepartment }) {
  const [scenario, setScenario] = React.useState("NORMAL");
  const S = {
    NORMAL: { open: 42, active: 9, ai: 35, op: 7, wait: 0, level: "ok", summary: "AI ведёт большинство диалогов. Очередь оператора пуста." },
    ATTENTION: { open: 58, active: 14, ai: 41, op: 13, wait: 4, level: "attention", summary: "Очередь оператора растёт, есть незавершённые платежи." },
    CRITICAL: { open: 73, active: 22, ai: 29, op: 35, wait: 9, level: "critical", summary: "Сбой исполнения заказов и переполненная очередь операторов." },
  }[scenario];

  return (
    <div>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 20 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 26, fontWeight: 700, letterSpacing: "-0.02em", color: "var(--text-heading)" }}>Командный центр</h1>
          <p style={{ margin: "6px 0 0", fontSize: 13.5, color: "var(--text-tertiary)" }}>Состояние компании одним взглядом · обновлено только что</p>
        </div>
        <select value={scenario} onChange={(e) => setScenario(e.target.value)} style={{ height: 36, borderRadius: 8, border: "1px solid var(--n-6)", padding: "0 10px", fontSize: 13 }}>
          <option value="NORMAL">Сценарий: Нормально</option>
          <option value="ATTENTION">Сценарий: Внимание</option>
          <option value="CRITICAL">Сценарий: Критично</option>
        </select>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 16, background: "#fff", border: "1px solid var(--n-8)", borderLeft: `3px solid ${scenario === "NORMAL" ? "#52c41a" : scenario === "ATTENTION" ? "#faad14" : "#ff4d4f"}`, borderRadius: 10, padding: "16px 20px", marginBottom: 20, boxShadow: "var(--shadow-xs)" }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 16, fontWeight: 600, color: "var(--text-heading)" }}>Компания:</span>
            <AttentionStatus level={S.level} />
          </div>
          <p style={{ margin: "3px 0 0", fontSize: 13.5, color: "var(--text-secondary)" }}>{S.summary}</p>
        </div>
        <div style={{ display: "flex", gap: 28 }}>
          <div style={{ textAlign: "right" }}><div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Отделы</div><div style={{ fontSize: 18, fontWeight: 600 }}>1</div></div>
          <div style={{ textAlign: "right" }}><div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>Выручка · сегодня</div><div style={{ fontSize: 18, fontWeight: 600, color: "var(--success-text)" }}>₽146 200</div></div>
        </div>
      </div>

      <div style={{ display: "flex", gap: 20, alignItems: "flex-start" }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 12 }}>Отделы</div>
          <DepartmentCard name="Продажи" meta="Ответственный: Анна Котова · 4 сотрудника · 1 AI-агент" level={S.level} summary={S.summary} onOpen={onOpenDepartment}>
            <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.05em", color: "var(--n-5)", margin: "16px 0 8px" }}>ДИАЛОГИ — СЕЙЧАС</div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 1, background: "var(--n-8)", border: "1px solid var(--n-8)", borderRadius: 9, overflow: "hidden" }}>
              <MetricCard label="Открытые диалоги" value={S.open} />
              <MetricCard label="Активны за 15 мин" value={S.active} />
              <MetricCard label="На AI" value={S.ai} dotColor="var(--ai)" />
              <MetricCard label="Ожидают оператора" value={S.wait} valueColor={S.wait > 0 ? "var(--warning-text)" : undefined} />
            </div>
          </DepartmentCard>
        </div>
        <div style={{ width: 320, flex: "none", display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ background: "#fff", border: "1px solid var(--n-8)", borderRadius: 12, boxShadow: "var(--shadow-sm)", overflow: "hidden" }}>
            <div style={{ padding: "15px 18px 12px", fontSize: 14, fontWeight: 600 }}>Состояние интеграций</div>
            <IntegrationHealthCard name="OpenRouter" group="AI-провайдер" status="connected" />
            <IntegrationHealthCard name="Точка" group="Платежи и фискализация" status={scenario === "NORMAL" ? "connected" : "degraded"} />
            <IntegrationHealthCard name="Fulfillment · FirePage" group="Исполнение" status={scenario === "CRITICAL" ? "error" : "connected"} />
          </div>
        </div>
      </div>
    </div>
  );
}
