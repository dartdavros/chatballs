const { Input, Button, Icon } = window.EdevsHubDesignSystem_e4c9df;

/* Recreation of design/baseline/AUTH · Вход.dc.html */
function AuthLoginPage({ onSuccess }) {
  const [email, setEmail] = React.useState("");
  const [pwd, setPwd] = React.useState("");
  const [show, setShow] = React.useState(false);
  const [error, setError] = React.useState(false);

  return (
    <div style={{ minHeight: "100%", minWidth: 1024, display: "flex", alignItems: "center", justifyContent: "center", background: "var(--surface-page)", fontFamily: "var(--font-sans)", padding: 24 }}>
      <div style={{ width: 400, maxWidth: "100%" }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", marginBottom: 24 }}>
          <img src="../../assets/logo-mark.svg" style={{ width: 48, height: 48, borderRadius: 13, marginBottom: 14, boxShadow: "0 4px 12px var(--primary-shadow)" }} />
          <h1 style={{ margin: 0, fontSize: 20, fontWeight: 700, letterSpacing: "-0.01em" }}>Edevs Hub</h1>
          <p style={{ margin: "5px 0 0", fontSize: 13, color: "var(--text-tertiary)" }}>Вход во внутренний кабинет</p>
        </div>
        <div style={{ background: "#fff", border: "1px solid var(--n-8)", borderRadius: 14, boxShadow: "var(--shadow-md)", padding: "26px 26px 24px" }}>
          {error && (
            <div style={{ display: "flex", gap: 10, padding: "11px 13px", background: "var(--error-bg)", border: "1px solid var(--error-border)", borderRadius: 9, marginBottom: 18 }}>
              <Icon name="alertCircle" size={16} color="var(--error-text)" />
              <span style={{ fontSize: 12.5, color: "var(--error-text)", lineHeight: 1.45 }}>Неверный email или пароль. Проверьте данные и попробуйте снова.</span>
            </div>
          )}
          <div style={{ marginBottom: 16 }}>
            <Input label="Email" icon={<Icon name="mail" size={16} color="var(--n-5)" />} value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@edevs.tech" />
          </div>
          <div style={{ marginBottom: 22 }}>
            <Input label="Пароль" type={show ? "text" : "password"} icon={<Icon name="lock" size={16} color="var(--n-5)" />}
              suffix={<button onClick={() => setShow(!show)} style={{ border: "none", background: "none", cursor: "pointer", color: "var(--n-5)", display: "flex" }}><Icon name={show ? "eye" : "eyeOff"} size={16} /></button>}
              value={pwd} onChange={(e) => setPwd(e.target.value)} placeholder="Пароль" />
          </div>
          <Button variant="primary" size="lg" onClick={() => (email && pwd ? onSuccess() : setError(true))}>Войти<Icon name="arrowRight" size={16} /></Button>
        </div>
        <p style={{ textAlign: "center", margin: "18px 0 0", fontSize: 12, color: "var(--n-5)" }}>Доступ только для сотрудников Edevs · защищённое соединение</p>
      </div>
    </div>
  );
}
