const { Icon, Avatar } = window.EdevsHubDesignSystem_e4c9df;

const NAV = [
  { key: "command", label: "Командный центр", icon: "dashboard" },
  { section: "КОМПАНИЯ" },
  { key: "departments", label: "Отделы", icon: "departments" },
  { key: "employees", label: "Сотрудники", icon: "employees" },
  { key: "products", label: "Продукты", icon: "products" },
  { section: "ПЛАТФОРМА" },
  { key: "ai", label: "AI", icon: "ai" },
  { key: "integrations", label: "Интеграции", icon: "integrations" },
  { key: "settings", label: "Настройки", icon: "settings" },
];

function HubShell({ page, onNavigate, crumb, children }) {
  return (
    <div style={{ display: "flex", height: "100%", minWidth: 1024, overflow: "hidden", background: "var(--surface-page)", fontFamily: "var(--font-sans)", color: "var(--text-body)" }}>
      <aside style={{ width: "var(--sidebar-width)", flex: "none", background: "#fff", borderRight: "1px solid var(--n-8)", display: "flex", flexDirection: "column" }}>
        <div style={{ height: "var(--h-topbar)", flex: "none", display: "flex", alignItems: "center", gap: 11, padding: "0 20px", borderBottom: "1px solid var(--n-9)" }}>
          <img src="../../assets/logo-mark.svg" style={{ width: 30, height: 30, borderRadius: 8 }} />
          <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.15 }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: "var(--text-heading)", letterSpacing: "-0.01em" }}>Edevs Hub</span>
            <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>Уровень компании</span>
          </div>
        </div>
        <nav style={{ flex: 1, overflowY: "auto", padding: "12px 12px 8px" }}>
          {NAV.map((item, i) =>
            item.section ? (
              <div key={i} style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.06em", color: "var(--n-5)", padding: "14px 12px 6px" }}>{item.section}</div>
            ) : (
              <a key={i} href="#" onClick={(e) => { e.preventDefault(); onNavigate(item.key); }}
                style={{
                  display: "flex", alignItems: "center", gap: 11, padding: "9px 12px", borderRadius: 8, textDecoration: "none",
                  marginBottom: 2, position: "relative", fontSize: 13.5,
                  fontWeight: page === item.key ? 600 : 500,
                  background: page === item.key ? "var(--primary-bg)" : "transparent",
                  color: page === item.key ? "#0958d9" : "var(--text-secondary)",
                }}>
                {page === item.key && <span style={{ position: "absolute", left: 0, top: 8, bottom: 8, width: 3, borderRadius: "0 3px 3px 0", background: "var(--primary)" }}></span>}
                <Icon name={item.icon} size={17} />
                {item.label}
              </a>
            )
          )}
        </nav>
        <div style={{ flex: "none", borderTop: "1px solid var(--n-9)", padding: "10px 12px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 11, padding: "8px 10px", borderRadius: 8 }}>
            <Avatar initials="ИП" />
            <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.2 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-body)" }}>Иван Петров</span>
              <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>OWNER</span>
            </div>
          </div>
        </div>
      </aside>

      <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
        <header style={{ height: "var(--h-topbar)", flex: "none", background: "#fff", borderBottom: "1px solid var(--n-8)", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 24px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--text-tertiary)" }}>
            <span style={{ fontWeight: 500, color: "var(--text-secondary)" }}>Edevs</span><span style={{ color: "var(--n-6)" }}>/</span>
            <span style={{ fontWeight: 600, color: "var(--text-body)" }}>{crumb}</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <button style={{ position: "relative", width: 36, height: 36, borderRadius: 8, border: "1px solid var(--n-8)", background: "#fff", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", color: "var(--text-secondary)" }}>
              <Icon name="bell" size={18} />
              <span style={{ position: "absolute", top: 6, right: 7, width: 8, height: 8, borderRadius: "50%", background: "var(--error)", border: "1.5px solid #fff" }}></span>
            </button>
            <div style={{ width: 1, height: 24, background: "var(--n-8)" }}></div>
            <Avatar initials="ИП" size={28} />
          </div>
        </header>
        <main style={{ flex: 1, overflowY: "auto", padding: "24px 28px 40px" }}>
          <div style={{ maxWidth: "var(--content-max)", margin: "0 auto" }}>{children}</div>
        </main>
      </div>
    </div>
  );
}
