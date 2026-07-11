const { CommerceStatusTimeline, Icon, Checkbox } = window.EdevsHubDesignSystem_e4c9df;

/* Recreation of design/baseline/CheckoutPanel.dc.html — the public
   pay.hub.edevs.tech checkout flow (SPEC-HUB-0007). Mobile-first, no Hub chrome. */
function CheckoutWidget() {
  const [st, setSt] = React.useState("checkout");
  const [buyer, setBuyer] = React.useState("person");
  const [pay, setPay] = React.useState("card");
  const [a1, setA1] = React.useState(false);
  const [a2, setA2] = React.useState(false);
  const ready = a1 && a2;

  const seg = (k) => ({
    flex: 1, height: 36, borderRadius: 8, border: "none", fontSize: 12.5, fontWeight: 600, cursor: "pointer",
    background: buyer === k ? "#1f1f1f" : "transparent", color: buyer === k ? "#fff" : "#8c8c8c",
  });
  const cardBox = (sel) => ({ display: "flex", alignItems: "center", gap: 12, width: "100%", padding: "11px 13px", borderRadius: 12, background: "#fff", cursor: "pointer", textAlign: "left", border: `1.5px solid ${sel ? "var(--primary)" : "#ececec"}`, boxShadow: sel ? "0 0 0 3px rgba(22,119,255,0.08)" : "none" });
  const dot = (sel) => ({ width: 18, height: 18, borderRadius: "50%", flex: "none", border: sel ? "5px solid var(--primary)" : "2px solid #d9d9d9", background: "#fff" });

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", width: "100%", background: "#f4f5f7", fontFamily: "var(--font-sans)", color: "#1f1f1f", overflow: "hidden" }}>
      <div style={{ flex: "none", background: "#fff", borderBottom: "1px solid #ececec", padding: "13px 18px", display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{ width: 30, height: 30, borderRadius: 8, background: "#1f1f1f", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: 14, fontWeight: 800, flex: "none" }}>F</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 14, fontWeight: 700, lineHeight: 1.1 }}>Foxray</div>
          <div style={{ fontSize: 11, color: "#9a9a9a", marginTop: 1 }}>Оформление покупки</div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 5, padding: "4px 9px", borderRadius: 7, background: "#f1f6ec", border: "1px solid #d7ead0", flex: "none" }}>
          <Icon name="shield" size={12} color="#3f8f3f" strokeWidth={2.2} /><span style={{ fontSize: 10.5, fontWeight: 600, color: "#3f8f3f" }}>Защищено</span>
        </div>
        <select value={st} onChange={(e) => setSt(e.target.value)} style={{ marginLeft: 8, fontSize: 10.5, border: "1px solid #ececec", borderRadius: 6, background: "#fafafa" }}>
          {["checkout","preparing","pending","paid","delivering","done","error","expired"].map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      <div style={{ flex: 1, minHeight: 0, overflowY: "auto" }}>
        {st === "expired" && <StateScreen icon="alertCircle" tone="#8c8c8c" title="Ссылка больше не действует" body="Сессия оформления истекла или была отменена. Вернитесь на сайт продукта." cta="Вернуться на foxray.pro" />}
        {st === "preparing" && <StateScreen spin title="Готовим оплату" body="Перенаправляем на защищённую страницу Банка Точка. Не закрывайте окно." />}
        {st === "pending" && <StateScreen icon="clock" tone="var(--warning-text)" toneBg="var(--warning-bg-strong)" title="Проверяем оплату" body="Банк ещё подтверждает операцию. Мы не создаём новый заказ автоматически." cta="Проверить ещё раз" />}
        {st === "error" && <StateScreen icon="xCircle" tone="var(--error-text)" toneBg="var(--error-bg)" title="Платёж не прошёл" body="Банк отклонил операцию. Деньги не списаны. Можно повторить оплату того же заказа." cta="Повторить оплату" />}

        {st === "paid" && (
          <div style={{ padding: "26px 16px 20px" }}>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center", marginBottom: 18 }}>
              <div style={{ width: 56, height: 56, borderRadius: "50%", background: "var(--success-bg-strong)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 14 }}><Icon name="check" size={28} color="#3f8f3f" strokeWidth={2.2} /></div>
              <h3 style={{ margin: 0, fontSize: 17, fontWeight: 700 }}>Оплата получена</h3>
              <p style={{ margin: "7px 0 0", fontSize: 13, color: "#6b6b6b" }}>Чек отправлен на <b style={{ color: "#262626" }}>a.kovalenko@northwind.ru</b></p>
            </div>
            <div style={{ background: "#fff", border: "1px solid #ececec", borderRadius: 13, padding: "14px 16px", display: "flex", flexDirection: "column", gap: 9 }}>
              <SummaryRow k="Заказ" v="HUB-2026-004187" mono /><SummaryRow k="Продукт" v="Foxray Max · 6 мест" /><SummaryRow k="Сумма" v="₽95 040" bold />
            </div>
          </div>
        )}

        {st === "delivering" && (
          <div style={{ padding: "26px 16px 20px" }}>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center", marginBottom: 16 }}>
              <div style={{ width: 56, height: 56, borderRadius: "50%", background: "var(--primary-bg)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 14 }}><Icon name="package2" size={27} color="var(--primary)" /></div>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Готовим доступ к продукту</h3>
              <p style={{ margin: "8px 0 0", fontSize: 13, color: "#6b6b6b" }}>Оплата прошла. Платить повторно не нужно.</p>
            </div>
            <div style={{ background: "#fff", border: "1px solid #ececec", borderRadius: 13, padding: "14px 16px" }}>
              <CommerceStatusTimeline steps={[{ label: "Оплата подтверждена · ₽95 040", state: "done" }, { label: "Подготовка рабочих мест", state: "active" }]} />
            </div>
          </div>
        )}

        {st === "done" && (
          <div style={{ padding: "26px 16px 20px" }}>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center", marginBottom: 18 }}>
              <div style={{ width: 56, height: 56, borderRadius: "50%", background: "var(--success-bg-strong)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 14 }}><Icon name="checkCircle" size={28} color="#3f8f3f" strokeWidth={2.2} /></div>
              <h3 style={{ margin: 0, fontSize: 17, fontWeight: 700 }}>Готово — доступ открыт</h3>
              <p style={{ margin: "7px 0 0", fontSize: 13, color: "#6b6b6b" }}>Foxray Max активирован на 6 мест.</p>
            </div>
            <a href="#" style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, height: 46, borderRadius: 10, background: "var(--primary)", color: "#fff", fontSize: 14, fontWeight: 600, textDecoration: "none" }}>Перейти в Foxray<Icon name="arrowRight" size={16} /></a>
          </div>
        )}

        {st === "checkout" && (
          <div style={{ padding: "16px 16px 24px", maxWidth: 520, margin: "0 auto" }}>
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.06em", color: "#9a9a9a", textTransform: "uppercase", marginBottom: 6 }}>Оформление подписки</div>
              <div style={{ fontSize: 19, fontWeight: 800, letterSpacing: "-0.01em" }}>Foxray Max</div>
              <div style={{ fontSize: 13, color: "#6b6b6b", marginTop: 3 }}>Годовая подписка · 6 рабочих мест</div>
            </div>

            <div style={{ background: "#fff", border: "1px solid #ececec", borderRadius: 13, overflow: "hidden", marginBottom: 14 }}>
              <div style={{ padding: "14px 16px 4px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12, marginBottom: 10 }}>
                  <div><div style={{ fontSize: 13, fontWeight: 600 }}>Foxray Max</div><div style={{ fontSize: 11.5, color: "#9a9a9a", marginTop: 2 }}>6 мест × ₽1 320 / мес · 12 мес</div></div>
                  <div style={{ fontSize: 13, fontWeight: 600, whiteSpace: "nowrap" }}>₽118 800</div>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}><span style={{ fontSize: 12.5, color: "#3f8f3f" }}>Скидка за годовую оплату · −20%</span><span style={{ fontSize: 12.5, fontWeight: 600, color: "#3f8f3f" }}>−₽23 760</span></div>
              </div>
              <div style={{ borderTop: "1px dashed #e8e8e8", padding: "12px 16px", display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
                <div><div style={{ fontSize: 13, fontWeight: 700 }}>Первый платёж</div><div style={{ fontSize: 11, color: "#9a9a9a", marginTop: 2 }}>Без НДС · валюта ₽ (RUB)</div></div>
                <div style={{ fontSize: 22, fontWeight: 800 }}>₽95 040</div>
              </div>
            </div>

            <div style={{ fontSize: 12.5, fontWeight: 700, margin: "0 2px 9px" }}>Покупатель</div>
            <div style={{ display: "flex", gap: 6, background: "#fff", border: "1px solid #ececec", borderRadius: 11, padding: 4, marginBottom: 12 }}>
              <button style={seg("person")} onClick={() => setBuyer("person")}>Физлицо</button>
              <button style={seg("ip")} onClick={() => setBuyer("ip")}>ИП</button>
              <button style={seg("company")} onClick={() => setBuyer("company")}>Юрлицо</button>
            </div>

            <div style={{ fontSize: 12.5, fontWeight: 700, margin: "0 2px 9px" }}>Способ оплаты</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 9, marginBottom: 14 }}>
              <button style={cardBox(pay === "card")} onClick={() => setPay("card")}>
                <div style={{ width: 38, height: 38, borderRadius: 9, background: "var(--primary-bg)", display: "flex", alignItems: "center", justifyContent: "center", flex: "none" }}><Icon name="card" size={19} color="var(--primary)" /></div>
                <div style={{ flex: 1, textAlign: "left" }}><div style={{ fontSize: 13.5, fontWeight: 600 }}>Банковская карта</div><div style={{ fontSize: 11.5, color: "#9a9a9a" }}>Автопродление подписки</div></div>
                <span style={dot(pay === "card")}></span>
              </button>
              <button style={cardBox(pay === "sbp")} onClick={() => setPay("sbp")}>
                <div style={{ width: 38, height: 38, borderRadius: 9, background: "var(--ai-bg)", display: "flex", alignItems: "center", justifyContent: "center", flex: "none" }}><Icon name="sbp" size={19} color="var(--ai)" /></div>
                <div style={{ flex: 1, textAlign: "left" }}><div style={{ fontSize: 13.5, fontWeight: 600 }}>СБП</div><div style={{ fontSize: 11.5, color: "#9a9a9a" }}>Система быстрых платежей</div></div>
                <span style={dot(pay === "sbp")}></span>
              </button>
            </div>

            <div style={{ background: "#fff", border: "1px solid #ececec", borderRadius: 13, padding: "14px 16px", display: "flex", flexDirection: "column", gap: 13, marginBottom: 90 }}>
              <Checkbox checked={a1} onChange={() => setA1(!a1)} label={<>Принимаю условия покупки и оферту, согласен с политикой обработки данных</>} />
              <Checkbox checked={a2} onChange={() => setA2(!a2)} label={<>Согласен на регулярные списания <b>₽95 040 / год</b> с автопродлением до отмены</>} />
            </div>
          </div>
        )}
      </div>

      {st === "checkout" && (
        <div style={{ flex: "none", background: "#fff", borderTop: "1px solid #ececec", padding: "11px 16px 14px", boxShadow: "var(--shadow-sticky)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 9 }}><span style={{ fontSize: 12.5, color: "#8c8c8c" }}>К оплате сегодня</span><span style={{ fontSize: 17, fontWeight: 800 }}>₽95 040</span></div>
          <button disabled={!ready} style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, width: "100%", height: 48, borderRadius: 11, border: "none", fontSize: 14.5, fontWeight: 700, cursor: ready ? "pointer" : "not-allowed", background: ready ? "var(--primary)" : "#e6e6e6", color: ready ? "#fff" : "#bfbfbf" }}>
            {ready ? "Перейти к оплате" : "Примите условия выше"}<Icon name="arrowRight" size={16} />
          </button>
        </div>
      )}
    </div>
  );
}

function StateScreen({ icon, tone = "var(--primary)", toneBg = "#f4f5f7", title, body, cta, spin }) {
  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center", padding: "40px 28px" }}>
      {spin ? (
        <div style={{ width: 38, height: 38, borderRadius: "50%", border: "3px solid #e6e6e6", borderTopColor: "var(--primary)", animation: "hub-spin .8s linear infinite", marginBottom: 20 }}></div>
      ) : (
        <div style={{ width: 54, height: 54, borderRadius: "50%", background: toneBg, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 18 }}><Icon name={icon} size={26} color={tone} /></div>
      )}
      <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>{title}</h3>
      <p style={{ margin: "9px 0 0", fontSize: 13, color: "#6b6b6b", lineHeight: 1.55, maxWidth: 300 }}>{body}</p>
      {cta && <button style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8, height: 44, padding: "0 22px", marginTop: 22, borderRadius: 10, background: "var(--primary)", color: "#fff", fontSize: 13.5, fontWeight: 600, border: "none", cursor: "pointer" }}>{cta}</button>}
    </div>
  );
}

function SummaryRow({ k, v, mono, bold }) {
  return <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}><span style={{ fontSize: 12.5, color: "#8c8c8c" }}>{k}</span><span style={{ fontSize: bold ? 14 : 12.5, fontWeight: 600, color: "#262626", fontFamily: mono ? "var(--font-mono)" : "inherit" }}>{v}</span></div>;
}
