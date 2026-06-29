import { EmptyState } from "../../../shared/ui";

export function SalesClientOrdersTab() {
  // Домена заказов в Хабе пока нет (ADR-HUB-0018: исполнение в бэкендах продуктов).
  return <EmptyState title="Заказы появятся после подключения домена продаж" />;
}
