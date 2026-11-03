import { t } from "../../../i18n";
import { FormField } from "../../../shared/form-controls";
import { LoadingState } from "../../../shared/ui";
import { Button } from "../../../shared/ui-controls";
import { useLinkSearch } from "./useLinkSearch";
import type { EntityLink } from "./api";

export function LinkSearch({ link, conversation, done }: { link: EntityLink; conversation: number; done: () => void }) {
  const state = useLinkSearch(link, conversation, done);
  return <div className="run-link-search">
    <p className="scenario-note">{link.service}</p>
    <FormField label={t("runs.record_search")} value={state.query} onChange={state.setQuery} disabled={state.busy} />
    <Button variant="secondary" disabled={state.busy || !state.query.trim()} onClick={() => void state.search()}>{t("runs.find_record")}</Button>
    <div className="run-link-results" aria-busy={state.busy}>
      {state.error ? <p className="run-step-error" role="alert">{state.error}</p> : state.busy ? <LoadingState />
        : state.items?.length === 0 ? <p>{t("runs.no_records")}</p> : state.items?.map(item => <label className="run-link-option" key={item.id}>
          <input type="radio" name="record-choice" checked={state.selected === item.id} onChange={() => state.select(item.id)} /><strong>{item.label}</strong>
        </label>)}
    </div>
    <Button variant="primary" disabled={state.busy || !state.selected} onClick={() => void state.apply()}>{t("runs.select_record")}</Button>
  </div>;
}
