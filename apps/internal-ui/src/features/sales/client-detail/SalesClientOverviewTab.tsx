import { Icon } from "../../../shared/icons";
import { Button } from "../../../shared/ui-controls";
import { ContactAvatar } from "../../conversations/ContactAvatar";
import { initialsOf } from "../clients/model";
import type { ClientDetailVm } from "./model";
import { t } from "../../../i18n";

// Вкладка «Обзор» (кадр K3): слева сводка и активность, справа — текущий
// диалог, ответственный и заметка (те же поля, что в контекст-панели чата).

export function SalesClientOverviewTab({ client, openConversation }: { client: ClientDetailVm; openConversation: (conversationId: number) => void }) {
  const current = client.dialogs.find((dialog) => dialog.active) ?? null;
  const noteDialog = client.dialogs.find((dialog) => dialog.note) ?? null;
  return (
    <div className="sales-client-overview">
      <div className="sales-client-overview-main">
        <div className="sales-client-summary">
          {client.summary.map((item) => (
            <div key={item.label}>
              <small>{item.label}</small>
              <strong className={`${item.accent ? "accent" : ""} ${item.compact ? "compact" : ""}`.trim()}>{item.value}</strong>
            </div>
          ))}
        </div>
        <ActivityList activity={client.activity} />
      </div>
      <div className="sales-client-overview-rail">
        {current && (
          <section className="sales-client-section-card">
            <div className="sales-client-section-head">
              <h3>{t("sales.current_conversation")}</h3>
              <span className="sales-client-mode" style={{ color: current.modeColor }}><i style={{ background: current.dot }} />{current.modeLabel}</span>
            </div>
            <p className="sales-client-current-title">«{current.title}»</p>
            <p className="sales-client-current-meta">
              <span style={{ color: current.agentColor }}><Icon name="robot" size={13} strokeWidth={2} />{current.agentName}</span>
              {current.channelLabel && <><i /><span>{current.channelLabel}</span></>}
              {current.groupName && <><i /><span className="sales-client-group"><em style={{ background: current.groupColor }} />{current.groupName}</span></>}
              <i /><span>{current.time}</span>
            </p>
            <Button className="sales-client-outline-action" variant="secondary" onClick={() => openConversation(current.id)}>{t("sales.open_conversation")}</Button>
          </section>
        )}
        {current?.assignee && (
          <section className="sales-client-section-card">
            <h3>{t("common.assignee")}</h3>
            <div className="sales-client-assignee">
              <ContactAvatar avatarUrl={current.assigneeAvatarUrl || undefined} initials={initialsOf(current.assignee)} background="var(--n-6)" className="sales-client-assignee-avatar" />
              <span><strong>{current.assignee}</strong><small>{t("sales.current_conversation_2")}</small></span>
            </div>
          </section>
        )}
        {noteDialog && (
          <section className="sales-client-note">
            <div>
              <h3>{t("conversations.note")}</h3>
              {(noteDialog.noteAuthor || noteDialog.noteAt) && <small>{[noteDialog.noteAuthor, noteDialog.noteAt].filter(Boolean).join(" · ")}</small>}
            </div>
            <p>{noteDialog.note}</p>
          </section>
        )}
      </div>
    </div>
  );
}

function ActivityList({ activity }: { activity: ClientDetailVm["activity"] }) {
  return (
    <section className="sales-client-section-card">
      <h3>{t("sales.last_activity")}</h3>
      {activity.length === 0 ? (
        <div className="sales-client-related-empty">{t("sales.no_events")}</div>
      ) : (
        <div className="sales-client-timeline">
          {activity.map((item, index) => (
            <div className="sales-client-timeline-row" key={`${item.title}-${item.time}-${index}`}>
              <div className="sales-client-timeline-mark"><span style={{ background: item.color }} />{index < activity.length - 1 && <i />}</div>
              <div className="sales-client-timeline-text">
                <div>{item.title}</div>
                <time>{item.time}</time>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
