import { EmptyState, LoadingState, PageHeader } from "../../shared/ui";
import { Pagination } from "../../shared/Pagination";
import { Button } from "../../shared/ui-controls";
import { pluralRu } from "../../shared/utils";
import { AuditFilters } from "./AuditFilters";
import { AuditTable } from "./AuditTable";
import { auditQueryIsDirty } from "./model";
import { useAudit } from "./useAudit";

// «Аудит действий» — отдельный экран из субменю «Настроек». Журнал отдавался
// последними 50 событиями без фильтров и без страниц: дальше пятидесятого
// события журнала просто не существовало. Теперь фильтры и страница считаются
// на сервере, а ширина и ритм — общие со списками раздела.

export function AuditPage() {
  const audit = useAudit();
  const { payload, loading, error, query, setQuery, reset } = audit;

  const header = (
    <PageHeader
      title="Аудит"
      text={payload
        ? `Журнал действий в организации · ${pluralRu(payload.total, ["событие", "события", "событий"])}`
        : "Журнал действий в организации"}
    />
  );

  if (error && !payload) {
    return (
      <div className="audit-page">
        {header}
        <EmptyState title={error} />
        <Button variant="secondary" onClick={() => void audit.reload()}>Повторить</Button>
      </div>
    );
  }

  if (!payload) {
    return <div className="audit-page">{header}<LoadingState /></div>;
  }

  const dirty = auditQueryIsDirty(query);

  return (
    <div className="audit-page">
      {header}
      <AuditFilters
        actors={payload.filters.actors}
        categories={payload.filters.categories}
        query={query}
        reset={reset}
        setQuery={setQuery}
      />
      {error && <div className="settings-section-error">{error}</div>}
      {/* Прошлую страницу не прячем на время загрузки — только гасим: иначе
          таблица моргает пустотой на каждый ввод в поиске. */}
      <div className={`audit-results ${loading ? "is-loading" : ""}`}>
        {payload.items.length === 0
          ? <EmptyState title={dirty ? "Под фильтры ничего не подошло" : "Событий пока нет"} />
          : <AuditTable events={payload.items} />}
      </div>
      {payload.pageCount > 1 && (
        <Pagination
          className="audit-pagination"
          note={`Показано ${payload.items.length} из ${payload.total} · по ${payload.pageSize} на странице`}
          page={payload.page}
          pageCount={payload.pageCount}
          onPage={(page) => setQuery({ page })}
        />
      )}
    </div>
  );
}
