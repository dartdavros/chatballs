import { Icon } from "../../../shared/icons";
import { EmptyState } from "../../../shared/ui";
import type { ClientDetailVm } from "./model";
import { t } from "../../../i18n";

// Вкладка «Диалоги» (кадр K4): тема и превью · агент · канал · группа ·
// статус · дата. Клик открывает диалог в чате.
export function SalesClientDialogsTab({ dialogs, openConversation }: { dialogs: ClientDetailVm["dialogs"]; openConversation: (conversationId: number) => void }) {
  if (dialogs.length === 0) return <EmptyState title={t("sales.contact_has_no_conversations_yet")} />;
  return (
    <div className="sales-client-dialogs">
      {dialogs.map((dialog) => (
        <button className="sales-client-dialog-row" type="button" onClick={() => openConversation(dialog.id)} key={dialog.id}>
          <span className="sales-client-dialog-main">
            <i style={{ background: dialog.dot }} />
            <span>
              <strong>{dialog.title}</strong>
              <small>{dialog.preview}</small>
            </span>
          </span>
          <span className="sales-client-dialog-agent" style={{ color: dialog.agentColor }}>
            <Icon name="robot" size={13} strokeWidth={2} />{dialog.agentName}
            {dialog.channelLabel && <em>· {dialog.channelLabel}</em>}
          </span>
          <span className="sales-client-dialog-group">
            {dialog.groupName ? <><i style={{ background: dialog.groupColor }} />{dialog.groupName}</> : <em>{t("common.no_group")}</em>}
          </span>
          <b style={{ background: dialog.modeBg, color: dialog.modeColor }}>{dialog.modeLabel}</b>
          <small>{dialog.time}</small>
        </button>
      ))}
    </div>
  );
}
