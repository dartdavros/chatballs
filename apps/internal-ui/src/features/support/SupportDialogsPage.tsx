import { EmptyState } from "../../shared/ui";

// SPEC-HUB-0010 §8.2: support inbox переиспользует общий conversation workspace.
// Посадочная страница (этап 2 — без данных); постраничная реализация inbox — этап 3
// (требует решения по §8.4 design gate / обобщению sales conversation-компонентов).
export function SupportDialogsPage() {
  return <EmptyState title="Диалоги поддержки появятся на следующем этапе" />;
}
