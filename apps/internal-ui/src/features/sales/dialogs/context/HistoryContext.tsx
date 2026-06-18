import { ContextSection } from "./ContextSection";

export function HistoryContext() {
  return (
    <div className="sales-history-context">
      <ContextSection title="ПРЕДЫДУЩИЕ ДИАЛОГИ">
        <div className="sales-history-card"><div><strong>Консультация по тарифам</strong><span>3 дня назад</span></div><p>FirePage · MAX · закрыт. Клиент уточнял лимиты тарифов, продажа не оформлена.</p></div>
        <div className="sales-history-card current"><div><strong>Текущий диалог</strong><span>сейчас</span></div><p>FirePage · MAX · ждёт оператора. Вопрос по amoCRM-интеграции для команды.</p></div>
      </ContextSection>
    </div>
  );
}
