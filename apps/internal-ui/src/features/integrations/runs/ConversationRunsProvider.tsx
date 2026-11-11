import { useEffect, type ReactNode } from "react";
import { Drawer } from "antd";
import { t } from "../../../i18n";
import { IconButton } from "../../../shared/ui-controls";
import { useMediaQuery } from "../../../shared/useMediaQuery";
import { ConversationRunsContext } from "./conversationContext";
import { useConversationRunsState } from "./useConversationRunsState";
import { ConversationRunContent } from "./ConversationRunPanel";
import "./runs.css";

export function ConversationRunsProvider({ conversationId, children, openContext }: { conversationId: number | null; children: ReactNode; openContext: () => void }) {
  const state = useConversationRunsState(conversationId);
  const mobile = useMediaQuery("(max-width: 767px)");
  const sheet = state.sheet;
  useEffect(() => { if (sheet && !mobile) openContext(); }, [sheet, mobile, openContext]);
  return <ConversationRunsContext.Provider value={state}>{children}
    <Drawer open={mobile && Boolean(sheet)} height="88vh" placement="bottom"
      push={false} closable={false} maskClosable={!sheet?.busy} keyboard={!sheet?.busy} onClose={state.close} className="run-conversation-drawer" title={sheet?.link ? t("runs.replace_link") : sheet?.action?.title ?? t("runs.details")}
      extra={<IconButton bare icon="close" label={t("common.close")} disabled={sheet?.busy} onClick={state.close} />}>
      {mobile && <ConversationRunContent />}
    </Drawer>
  </ConversationRunsContext.Provider>;
}
