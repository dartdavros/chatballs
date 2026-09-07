import { useState } from "react";

import { DecisionDialog } from "../../shared/DecisionDialog";
import { StatusPill } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import { shortDateTime } from "../../shared/utils";
import {
  changePortalStatus,
  portalErrorMessage,
  PORTAL_STATUS_LABEL,
  type PortalStatus,
  type SupportPortal,
} from "./model";

// Раздел «Публикация и архив» субменю настроек (кадры PT4–PT6): здесь живут
// действия, которые в шапке карточки спрятаны в ⋯.

const COPY: Record<Exclude<PortalStatus, "ARCHIVED"> | "ARCHIVED", { title: string; description: string }> = {
  PUBLISHED: {
    title: "Опубликовать портал?",
    description: "Опубликованные статьи станут доступны по публичному адресу.",
  },
  DRAFT: {
    title: "Снять портал с публикации?",
    description: "Посетители перестанут видеть материалы, адрес останется за порталом.",
  },
  ARCHIVED: {
    title: "Перенести портал в архив?",
    description: "Портал и его материалы станут недоступны посетителям до восстановления.",
  },
};

export function PortalPublishSettings({
  canManage,
  portal,
  onChanged,
}: {
  canManage: boolean;
  portal: SupportPortal;
  onChanged: (portal: SupportPortal) => void;
}) {
  const [pending, setPending] = useState<PortalStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function apply(status: PortalStatus) {
    setBusy(true);
    setError("");
    try {
      const payload = await changePortalStatus(portal.id, status);
      onChanged(payload.portal);
      setPending(null);
    } catch (caught) {
      setError(portalErrorMessage(caught, "Не удалось изменить статус портала"));
      setPending(null);
    } finally {
      setBusy(false);
    }
  }

  const archived = portal.status === "ARCHIVED";
  return (
    <div className="portal-settings-card">
      <div className="portal-status-row">
        <span>
          <small>Текущее состояние</small>
          <StatusPill
            status={portal.status === "PUBLISHED" ? "published" : archived ? "archived" : "draft"}
            label={PORTAL_STATUS_LABEL[portal.status]}
          />
        </span>
        {portal.publishedAt && <span className="portal-settings-note">опубликован {shortDateTime(portal.publishedAt)}</span>}
      </div>

      {canManage && (
        <div className="portal-settings-actions">
          {portal.status === "DRAFT" && <Button variant="primary" disabled={busy} onClick={() => setPending("PUBLISHED")}>Опубликовать портал</Button>}
          {portal.status === "PUBLISHED" && <Button variant="secondary" disabled={busy} onClick={() => setPending("DRAFT")}>Снять с публикации</Button>}
          {archived && <Button variant="secondary" disabled={busy} onClick={() => void apply("DRAFT")}>Вернуть из архива</Button>}
          <span className="portal-settings-gap" />
          {!archived && <Button variant="danger-outline" disabled={busy} onClick={() => setPending("ARCHIVED")}>Перенести в архив</Button>}
        </div>
      )}
      <p className="portal-dns-note">
        Архивный портал перестаёт открываться по публичному адресу, а его материалы исчезают из
        ответов агента. Ничего не удаляется: портал можно вернуть из архива.
      </p>
      {error && <div className="portal-form-error">{error}</div>}

      <DecisionDialog
        open={pending !== null}
        onClose={() => setPending(null)}
        tone={pending === "ARCHIVED" ? "danger" : "warning"}
        icon={pending === "ARCHIVED" ? "trash" : "check"}
        title={pending ? COPY[pending].title : ""}
        description={pending ? COPY[pending].description : ""}
        actions={<>
          <Button variant="secondary" onClick={() => setPending(null)}>Отмена</Button>
          <Button
            variant={pending === "ARCHIVED" ? "danger-outline" : "primary"}
            disabled={busy}
            onClick={() => pending && void apply(pending)}
          >
            {pending === "ARCHIVED" ? "В архив" : pending === "DRAFT" ? "Снять" : "Опубликовать"}
          </Button>
        </>}
      />
    </div>
  );
}
