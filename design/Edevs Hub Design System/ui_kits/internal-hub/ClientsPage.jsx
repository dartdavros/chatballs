const { Avatar, Tag, Icon } = window.EdevsHubDesignSystem_e4c9df;

const DATA = [
  { name: "Мария Соколова", initials: "МС", color: "#eb6f4b", cid: "CUS-4821", email: "m.sokolova@workmail.ru", ch: ["MAX"], pr: ["FP"], last: "5 мин назад", open: 1, orders: 0, total: "—" },
  { name: "Дмитрий Орлов", initials: "ДО", color: "#3b82c4", cid: "CUS-4789", email: "d.orlov@gmail.com", ch: ["TG"], pr: ["FX"], last: "8 мин назад", open: 1, orders: 2, total: "₽4 980" },
  { name: "Елена Кузнецова", initials: "ЕК", color: "#9254de", cid: "CUS-4702", email: "e.kuznetsova@corp.ru", ch: ["MAX", "WEB"], pr: ["FX", "FP"], last: "18 мин назад", open: 1, orders: 3, total: "₽12 470" },
  { name: "Сергей Волков", initials: "СВ", color: "#13a8a8", cid: "CUS-4655", email: "s.volkov@mail.ru", ch: ["TG"], pr: ["FP"], last: "26 мин назад", open: 1, orders: 1, total: "₽2 490" },
  { name: "Павел Новиков", initials: "ПН", color: "#52a838", cid: "CUS-4410", email: "p.novikov@firm.io", ch: ["MAX"], pr: ["FP"], last: "1 ч назад", open: 0, orders: 4, total: "₽19 600" },
];
const CH = { MAX: { l: "MAX", c: "var(--channel-max)", bg: "var(--channel-max-bg)" }, TG: { l: "TG", c: "var(--channel-telegram)", bg: "var(--channel-telegram-bg)" }, WEB: { l: "Web", c: "var(--channel-webchat)", bg: "var(--channel-webchat-bg)" } };
const PR = { FP: { n: "FirePage", tone: "primary" }, FX: { n: "Foxray", tone: "ai" } };

function ClientsPage() {
  const [q, setQ] = React.useState("");
  const rows = DATA.filter((d) => !q || d.name.toLowerCase().includes(q.toLowerCase()));
  return (
    <div>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 18 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 24, fontWeight: 700, letterSpacing: "-0.02em", color: "var(--text-heading)" }}>Клиенты</h1>
          <p style={{ margin: "6px 0 0", fontSize: 13.5, color: "var(--text-tertiary)" }}>Контакты отдела продаж · показано {rows.length} из 248</p>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 12, background: "#fff", border: "1px solid var(--n-8)", borderRadius: 11, padding: "11px 14px", marginBottom: 16, boxShadow: "var(--shadow-xs)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, height: 34, padding: "0 11px", border: "1px solid var(--n-7)", borderRadius: 8, background: "var(--surface-sunken)", width: 280 }}>
          <Icon name="search" size={15} color="var(--n-5)" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Поиск по имени или email…" style={{ border: "none", outline: "none", background: "transparent", fontSize: 13, width: "100%", fontFamily: "inherit" }} />
        </div>
      </div>

      <div style={{ background: "#fff", border: "1px solid var(--n-8)", borderRadius: 12, boxShadow: "var(--shadow-sm)", overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: "var(--n-10)" }}>
              {["КЛИЕНТ", "КАНАЛЫ", "ПРОДУКТЫ", "ПОСЛ. ДИАЛОГ", "ОТКР.", "ЗАКАЗЫ", "СУММА ПОКУПОК"].map((h, i) => (
                <th key={i} style={{ textAlign: i >= 4 ? "right" : "left", padding: "11px 12px", fontSize: 11, fontWeight: 600, color: "var(--text-tertiary)", borderBottom: "1px solid var(--n-8)" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} style={{ borderBottom: "1px solid var(--n-9)" }}>
                <td style={{ padding: "12px 16px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 11 }}>
                    <Avatar initials={r.initials} color={r.color} size={34} />
                    <div><a href="#" style={{ fontWeight: 600, color: "var(--primary)", textDecoration: "none", fontSize: 13.5 }}>{r.name}</a><div style={{ fontSize: 11, color: "var(--n-5)", fontFamily: "var(--font-mono)" }}>{r.cid}</div></div>
                  </div>
                </td>
                <td style={{ padding: "12px" }}><div style={{ display: "flex", gap: 5 }}>{r.ch.map((c) => <span key={c} style={{ display: "inline-flex", alignItems: "center", gap: 4, padding: "2px 7px", borderRadius: 5, background: CH[c].bg }}><span style={{ width: 5, height: 5, borderRadius: "50%", background: CH[c].c }}></span><span style={{ fontSize: 10.5, fontWeight: 600, color: CH[c].c }}>{CH[c].l}</span></span>)}</div></td>
                <td style={{ padding: "12px" }}><div style={{ display: "flex", gap: 5 }}>{r.pr.map((p) => <Tag key={p} tone={PR[p].tone}>{PR[p].n}</Tag>)}</div></td>
                <td style={{ padding: "12px", color: "var(--text-secondary)" }}>{r.last}</td>
                <td style={{ padding: "12px", textAlign: "right", fontWeight: 600, color: r.open > 0 ? "var(--warning-text)" : "var(--n-5)" }}>{r.open}</td>
                <td style={{ padding: "12px", textAlign: "right", color: "var(--text-secondary)" }}>{r.orders}</td>
                <td style={{ padding: "12px", textAlign: "right", fontWeight: 600 }}>{r.total}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
