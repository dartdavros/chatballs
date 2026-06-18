import type { ReactNode } from "react";

import { Icon } from "../../../shared/icons";
import type { RightTab } from "./types";

export function SalesContextPanel({ rightTab, setRightTab }: { rightTab: RightTab; setRightTab: (tab: RightTab) => void }) {
  return (
    <section className="sales-context">
      <div className="sales-context-tabs">
        <RightTabButton active={rightTab === "client"} onClick={() => setRightTab("client")}>Клиент</RightTabButton>
        <RightTabButton active={rightTab === "product"} onClick={() => setRightTab("product")}>Продукт</RightTabButton>
        <RightTabButton active={rightTab === "history"} onClick={() => setRightTab("history")}>История</RightTabButton>
      </div>
      <div className="sales-context-body">
        {rightTab === "client" && <ClientContext />}
        {rightTab === "product" && <ProductContext />}
        {rightTab === "history" && <HistoryContext />}
      </div>
    </section>
  );
}

function RightTabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return <button className={active ? "active" : ""} onClick={onClick}>{children}</button>;
}

function ClientContext() {
  return (
    <div className="sales-client-context">
      <div className="sales-client-hero"><span>МС</span><strong>Мария Соколова</strong><em><Icon name="check" size={11} />Согласие получено</em></div>
      <ContextSection title="КАНАЛЫ И КОНТАКТЫ">
        <ContactRow dot="#6b5be0" title="MAX" text="@maria.s" note="основной" />
        <ContactRow icon="mail" title="m.sokolova@workmail.ru" text="Email · подтверждён" mono />
        <ContactRow icon="phone" title="+7 ··· ·· 14" text="Телефон · скрыт" muted />
      </ContextSection>
      <ContextSection title="РАБОЧАЯ ЗАМЕТКА" action="Изменить">
        <div className="sales-note">Команда ~8 человек, интересует <b>FirePage Business</b> помесячно. Открытый вопрос — интеграция с их CRM (amoCRM).</div>
      </ContextSection>
      <ContextSection title="СВОДКА">
        <div className="sales-summary-grid"><div><span>Заказы</span><b>0</b></div><div><span>Диалоги</span><b>2</b></div><div><span>Покупки</span><b>₽0</b></div></div>
        <p className="sales-context-muted">Первый контакт: сегодня, 14:02</p>
      </ContextSection>
      <ContextSection title="ДЕЙСТВИЯ OWNER">
        <button className="sales-context-action">Объединить контакты</button>
        <button className="sales-context-action danger">Обезличить данные</button>
      </ContextSection>
    </div>
  );
}

function ProductContext() {
  return (
    <div className="sales-product-context">
      <div className="sales-product-head"><span><Icon name="box" size={20} /></span><div><strong>FirePage</strong><small>Конструктор лендингов · активен</small></div></div>
      <ContextSection title="ПОДХОДЯЩИЕ OFFER">
        <div className="sales-offer active"><div><strong>Business</strong><em>AI может предлагать</em></div><p><b>₽2 490</b><span>/ мес · помесячно</span></p><small>До 10 пользователей · общие проекты · amoCRM-интеграция · приоритетная поддержка.</small></div>
        <div className="sales-offer"><div><strong>Pro</strong><em>для одного</em></div><p><b>₽990</b><span>/ мес</span></p><small>1 пользователь · все шаблоны · базовая поддержка.</small></div>
      </ContextSection>
    </div>
  );
}

function HistoryContext() {
  return (
    <div className="sales-history-context">
      <ContextSection title="ПРЕДЫДУЩИЕ ДИАЛОГИ">
        <div className="sales-history-card"><div><strong>Консультация по тарифам</strong><span>3 дня назад</span></div><p>FirePage · MAX · закрыт. Клиент уточнял лимиты тарифов, продажа не оформлена.</p></div>
        <div className="sales-history-card current"><div><strong>Текущий диалог</strong><span>сейчас</span></div><p>FirePage · MAX · ждёт оператора. Вопрос по amoCRM-интеграции для команды.</p></div>
      </ContextSection>
    </div>
  );
}

function ContextSection({ title, action, children }: { title: string; action?: string; children: ReactNode }) {
  return <section className="sales-context-section"><div className="sales-context-section-head"><h4>{title}</h4>{action && <button>{action}</button>}</div>{children}</section>;
}

function ContactRow({ dot, icon, title, text, note, mono = false, muted = false }: { dot?: string; icon?: "mail" | "phone"; title: string; text: string; note?: string; mono?: boolean; muted?: boolean }) {
  return (
    <div className="sales-contact-row">
      <span>{dot && <i style={{ background: dot }} />}{icon && <Icon name={icon} size={15} />}</span>
      <div><strong className={`${mono ? "mono" : ""} ${muted ? "muted" : ""}`}>{title}</strong><small>{text}</small></div>
      {note && <em>{note}</em>}
    </div>
  );
}
