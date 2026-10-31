import { useEffect, useMemo, useState } from "react";
import { fmt, t, tn } from "../../../i18n";
import { Pagination } from "../../../shared/Pagination";
import { Avatar } from "../../../shared/ui";
import { Button } from "../../../shared/ui-controls";
import { JournalFilters, emptyJournalQuery } from "./JournalFilters";
import { getRetention } from "./api";
import { RunStatus } from "./RunStatus";
import { useRuns } from "./useRuns";

export function RunJournal({ open, openRetention }: { open: (id: string) => void; openRetention: () => void }) {
  const [filters, setFilters] = useState(emptyJournalQuery);
  const [page, setPage] = useState(1);
  const [retention, setRetention] = useState({ stepDays: 7, journalDays: 30 });
  const query = useMemo(() => new URLSearchParams({ ...filters, page: String(page) }), [filters, page]);
  const result = useRuns(query);
  useEffect(() => { let active = true; getRetention().then(value => { if (active) setRetention(value); }).catch(() => undefined); return () => { active = false; }; }, []);
  return <>
    <JournalFilters value={filters} change={value => { setFilters(value); setPage(1); }} filters={result.data?.filters} />
    <div className="run-table"><div className="run-table-row is-head"><span>{t("runs.number")}</span><span>{t("runs.scenario")}</span><span>{t("runs.initiator")}</span><span>{t("runs.where")}</span><span>{t("runs.started")}</span><span>{t("runs.state")}</span></div>
      <div className="run-table-body" aria-busy={result.loading}>{result.loading ? Array.from({ length: 9 }, (_, row) => <div className="run-table-row run-skeleton" key={row} aria-hidden="true">{Array.from({ length: 6 }, (_, column) => <i key={column} />)}</div>)
        : result.error ? <div className="run-empty"><strong>{result.error}</strong><p>{t("runs.load_failed_text")}</p><Button variant="secondary" onClick={() => void result.reload()}>{t("runs.retry")}</Button></div>
        : !result.data?.items.length ? <div className="run-empty"><strong>{t(filters.q || filters.connection || filters.initiator || filters.group ? "runs.nothing_found" : "runs.empty")}</strong><p>{t(filters.q || filters.connection || filters.initiator || filters.group ? "runs.change_filters" : "runs.empty_text")}</p></div>
        : result.data.items.map(run => <div className="run-table-row" key={run.id}><span className="mono">{fmt.number(run.number)}</span>
          <div><button type="button" className="link is-strong" onClick={() => open(run.id)}>{run.name}</button><small>{run.connection}</small></div>
          <span className="run-initiator"><Avatar employee={{ fullName: run.initiator, email: "", avatarUrl: "" }} />{run.initiator}</span><span>{run.conversationId ? fmt.number(run.conversationId) : "—"}</span><span>{fmt.shortDateTime(run.createdAt)}</span><RunStatus state={run.state} label={run.stateLabel} /></div>)}
      </div><Pagination className="run-pagination" page={page} pageCount={Math.max(1, Math.ceil((result.data?.count ?? 0) / 25))}
        onPage={next => { if (!result.loading) setPage(next); }} note={result.loading ? t("runs.loading") : t("runs.shown", { shown: fmt.number(result.data?.items.length ?? 0), count: fmt.number(result.data?.count ?? 0) })} />
    </div>
    <p className="run-retention-note">{t("runs.retention_note", { stepDays: tn("runs.days", retention.stepDays), journalDays: tn("runs.days", retention.journalDays) })}{" "}<button type="button" className="link" onClick={openRetention}>{t("runs.retention_link")}</button></p>
  </>;
}
