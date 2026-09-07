import { useState } from "react";

import { Segmented } from "../../shared/ui";
import { FilterDropdown, SearchInput } from "../../shared/ui-controls";
import {
  AUDIT_PERIODS,
  auditQueryIsDirty,
  type AuditFilterOption,
  type AuditPeriod,
  type AuditQuery,
} from "./model";

// Фильтры журнала: поиск · период · раздел · сотрудник · результат · «Сбросить».
// Те же контролы, что у списков Сотрудников и Контактов — SearchInput,
// FilterDropdown и Segmented. Период — пресетами, а не календарём: журнал
// смотрят «что было сегодня» и «что было за неделю».

export function AuditFilters({ actors, categories, query, setQuery, reset }: {
  actors: AuditFilterOption[];
  categories: AuditFilterOption[];
  query: AuditQuery;
  setQuery: (patch: Partial<AuditQuery>) => void;
  reset: () => void;
}) {
  const [periodOpen, setPeriodOpen] = useState(false);
  const [categoryOpen, setCategoryOpen] = useState(false);
  const [actorOpen, setActorOpen] = useState(false);

  const periodLabel = AUDIT_PERIODS.find(([value]) => value === query.period)?.[1] ?? "";
  const categoryLabel = categories.find((item) => item.value === query.category)?.label ?? "Все";
  const actorLabel = actors.find((item) => item.value === query.actor)?.label ?? "Все";

  return (
    <div className="audit-filters">
      <SearchInput
        className="audit-search"
        hotkey="/"
        placeholder="Поиск по действию, объекту или сотруднику…"
        value={query.q}
        onChange={(value) => setQuery({ q: value })}
      />
      <FilterDropdown
        caption="Период"
        label={periodLabel}
        open={periodOpen}
        options={AUDIT_PERIODS.map(([value, label]) => ({ value, label }))}
        selected={[query.period]}
        onOpenChange={setPeriodOpen}
        onSelect={(value) => setQuery({ period: value as AuditPeriod })}
      />
      <FilterDropdown
        caption="Раздел"
        label={categoryLabel}
        open={categoryOpen}
        options={[{ value: "", label: "Все" }, ...categories]}
        selected={query.category ? [query.category] : []}
        onOpenChange={setCategoryOpen}
        onSelect={(value) => setQuery({ category: value })}
      />
      {actors.length > 1 && (
        <FilterDropdown
          caption="Сотрудник"
          label={actorLabel}
          open={actorOpen}
          options={[{ value: "", label: "Все" }, ...actors]}
          selected={query.actor ? [query.actor] : []}
          onOpenChange={setActorOpen}
          onSelect={(value) => setQuery({ actor: value })}
        />
      )}
      <Segmented
        items={[["", "Все"], ["SUCCESS", "Выполнено"], ["DENIED", "Отклонено"], ["FAILED", "Ошибка"]]}
        value={query.result}
        setValue={(value) => setQuery({ result: value })}
      />
      <div className="audit-filters-spacer" />
      <button
        className={`audit-reset ${auditQueryIsDirty(query) ? "is-dirty" : ""}`}
        type="button"
        onClick={reset}
      >
        Сбросить
      </button>
    </div>
  );
}
