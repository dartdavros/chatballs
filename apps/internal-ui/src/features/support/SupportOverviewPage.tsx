import { EmptyState } from "../../shared/ui";

// SPEC-HUB-0010 §12: Support Overview показывает операционные метрики (открытые
// обращения, ожидают оператора, AI/оператор, закрытые, breakdown по продуктам).
// Sales/revenue/conversion запрещены. Backend support-метрики — следующий этап
// (stats.py сейчас sales-only), поэтому посадочная без выдуманных данных.
export function SupportOverviewPage() {
  return (
    <div className="sales-overview-header">
      <div>
        <h1>Обзор отдела поддержки</h1>
        <p>Операционное состояние обращений клиентов продуктов</p>
      </div>
      <EmptyState title="Метрики поддержки появятся на следующем этапе" />
    </div>
  );
}
