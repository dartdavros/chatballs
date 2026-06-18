import { Icon } from "../../../../shared/icons";
import { ContactRow } from "./ContactRow";
import { ContextSection } from "./ContextSection";

export function ClientContext() {
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
