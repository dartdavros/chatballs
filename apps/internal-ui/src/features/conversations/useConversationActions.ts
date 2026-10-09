import {
  claimConversation, closeConversation, deleteConversation, markConversationAsSpam,
  releaseConversation, returnToQueue, type ApiConversation,
} from "./model";
import { t } from "../../i18n";

export function useConversationActions({ selectedId, applyUpdated, clearSelected, setError }: {
  selectedId: number | null;
  applyUpdated: (updated: ApiConversation) => void;
  clearSelected: () => void;
  setError: (error: string) => void;
}) {
  async function update(action: (id: number) => Promise<ApiConversation>): Promise<boolean> {
    if (selectedId == null) return false;
    setError("");
    try {
      applyUpdated(await action(selectedId));
      return true;
    } catch (error) {
      setError(error instanceof Error ? error.message : t("common.could_not_complete_action"));
      return false;
    }
  }
  async function onDelete() {
    if (selectedId == null) return false;
    setError("");
    try {
      await deleteConversation(selectedId);
      clearSelected();
      return true;
    } catch (error) {
      setError(error instanceof Error ? error.message : t("conversations.could_not_delete_conversation"));
      return false;
    }
  }
  return {
    onClaim: () => { void update(claimConversation); },
    onRelease: () => { void update(releaseConversation); },
    onReturnQueue: () => { void update(returnToQueue); },
    onClose: () => { void update(closeConversation); },
    onSpam: () => update(markConversationAsSpam), onDelete,
  };
}
