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
import { t } from "../../i18n";

// Раздел «Публикация и архив» субменю настроек (кадры PT4–PT6): здесь живут
// действия, которые в шапке карточки спрятаны в ⋯.

const COPY: Record<Exclude<PortalStatus, "ARCHIVED"> | "ARCHIVED", { title: string; description: string }> = {
  PUBLISHED: {
    title: t("portals.publish_portal_2"),
    description: t("portals.published_articles_will_become_available"),
  },
  DRAFT: {
    title: t("portals.unpublish_portal"),
    description: t("portals.visitors_will_stop_seeing_material"),
  },
  ARCHIVED: {
    title: t("portals.move_portal_archive"),
    description: t("portals.portal_its_material_become_unavailable"),
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
      setError(portalErrorMessage(caught, t("portals.could_not_change_portal_status")));
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
          <small>{t("portals.current_state")}</small>
          <StatusPill
            status={portal.status === "PUBLISHED" ? "published" : archived ? "archived" : "draft"}
            label={PORTAL_STATUS_LABEL[portal.status]}
          />
        </span>
        {portal.publishedAt && <span className="portal-settings-note">{t("portals.published_at_lower", { date: shortDateTime(portal.publishedAt) })}</span>}
      </div>

      {canManage && (
        <div className="portal-settings-actions">
          {portal.status === "DRAFT" && <Button variant="primary" disabled={busy} onClick={() => setPending("PUBLISHED")}>{t("portals.publish_portal")}</Button>}
          {portal.status === "PUBLISHED" && <Button variant="secondary" disabled={busy} onClick={() => setPending("DRAFT")}>{t("portals.unpublish")}</Button>}
          {archived && <Button variant="secondary" disabled={busy} onClick={() => void apply("DRAFT")}>{t("portals.restore_from_archive")}</Button>}
          <span className="portal-settings-gap" />
          {!archived && <Button variant="danger-outline" disabled={busy} onClick={() => setPending("ARCHIVED")}>{t("common.move_archive")}</Button>}
        </div>
      )}
      <p className="portal-dns-note">
        {t("portals.archive_note")}
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
          <Button variant="secondary" onClick={() => setPending(null)}>{t("common.cancel")}</Button>
          <Button
            variant={pending === "ARCHIVED" ? "danger-outline" : "primary"}
            disabled={busy}
            onClick={() => pending && void apply(pending)}
          >
            {pending === "ARCHIVED" ? t("common.archive") : pending === "DRAFT" ? t("portals.unpublish_2") : t("common.publish")}
          </Button>
        </>}
      />
    </div>
  );
}
