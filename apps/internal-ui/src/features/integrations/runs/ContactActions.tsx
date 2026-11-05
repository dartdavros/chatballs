import { t } from "../../../i18n";
import { LoadingState } from "../../../shared/ui";
import { useConversationRuns } from "./conversationContext";
import { ContactEntityLinks } from "../entity-links/ContactEntityLinks";
import { ManualActionMenu } from "./ManualActionMenu";

export function ContactActions() {
  const state = useConversationRuns();
  if (!state) return null;
  return <><section className="run-contact-actions"><h4>{t("runs.actions")}</h4>{state.loading ? <LoadingState variant="inline" />
    : state.error ? <p role="alert">{state.error}</p>
    : state.catalog?.items.length ? <ManualActionMenu />
    : <p>{t("runs.no_actions_text")}</p>}</section><ContactEntityLinks /></>;
}
