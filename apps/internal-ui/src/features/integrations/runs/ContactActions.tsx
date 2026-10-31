import { t } from "../../../i18n";
import { LoadingState } from "../../../shared/ui";
import { useConversationRuns } from "./conversationContext";

export function ContactActions() {
  const state = useConversationRuns();
  if (!state) return null;
  return <section className="run-contact-actions"><h4>{t("runs.actions")}</h4>{state.loading ? <LoadingState variant="inline" />
    : state.error ? <p role="alert">{state.error}</p>
    : state.catalog?.items.length ? state.catalog.items.map(action => <button type="button" className="link" key={`${action.kind}:${action.id}`}
      disabled={action.available === false} title={action.reason} onClick={() => state.openAction(action)}>{action.title}</button>)
    : <p>{t("runs.no_actions_text")}</p>}</section>;
}
