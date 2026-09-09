import { useCallback, useEffect, useState } from "react";

import { hasCapability } from "../../auth/access";
import { DecisionDialog } from "../../shared/DecisionDialog";
import { ErrorScreen, LoadingState } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import type { SessionUser } from "../../types";
import {
  changePortalStatus,
  listPortalCategories,
  listSupportPortals,
  loadSupportPortal,
  portalErrorMessage,
  publishArticleRevision,
  type PortalAddressConfig,
  type PortalArticle,
  type PortalCategory,
  type PortalStatus,
  type SupportPortal,
} from "./model";
import { PortalArticleEditor } from "./PortalArticleEditor";
import { PortalHeader } from "./PortalHeader";
import { PortalLibrary } from "./PortalLibrary";
import { PortalSettings } from "./PortalSettings";
import type { PortalSettingsSectionKey } from "./sections";
import "./styles";
import { t } from "../../i18n";

// Карточка портала (дизайн-базлайн v2, кадры PT3–PT8): общая шапка с публичным
// адресом, под ней — библиотека материалов, настройки или редактор статьи.

type Publishing = { article: PortalArticle; revisionId: number };

export function SupportPortalDetailPage({
  portalId,
  section,
  user,
  openPortals,
  openPortalContent,
  openPortalSettings,
}: {
  portalId: number | null;
  section: PortalSettingsSectionKey | null;
  user: SessionUser;
  openPortals: () => void;
  openPortalContent: (portalId: number) => void;
  openPortalSettings: (portalId: number, section?: PortalSettingsSectionKey) => void;
}) {
  const [portal, setPortal] = useState<SupportPortal | null>(null);
  const [address, setAddress] = useState<PortalAddressConfig | null>(null);
  const [categories, setCategories] = useState<PortalCategory[]>([]);
  const [editing, setEditing] = useState<PortalArticle | null | undefined>(undefined);
  const [publishing, setPublishing] = useState<Publishing | null>(null);
  const [pendingStatus, setPendingStatus] = useState<PortalStatus | null>(null);
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const canManage = hasCapability(user, "support.operate");

  const load = useCallback(async () => {
    if (!portalId) return;
    setFailed(false);
    try {
      // Статьи грузит сама библиотека — постранично, со своими фильтрами.
      const [portalPayload, categoryPayload, listPayload] = await Promise.all([
        loadSupportPortal(portalId),
        listPortalCategories(portalId),
        listSupportPortals(),
      ]);
      setPortal(portalPayload.portal);
      setCategories(categoryPayload.items);
      setAddress(listPayload.address);
    } catch {
      setFailed(true);
    }
  }, [portalId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function setStatus(status: PortalStatus) {
    if (!portal) return;
    setBusy(true);
    setError("");
    try {
      const payload = await changePortalStatus(portal.id, status);
      setPortal(payload.portal);
      setPendingStatus(null);
    } catch (caught) {
      setError(portalErrorMessage(caught, t("portals.could_not_change_portal_status")));
      setPendingStatus(null);
    } finally {
      setBusy(false);
    }
  }

  async function publish() {
    if (!publishing || !portal) return;
    setBusy(true);
    setError("");
    try {
      await publishArticleRevision(portal.id, publishing.article.id, publishing.revisionId);
      setPublishing(null);
      setEditing(undefined);
      await load();
    } catch (caught) {
      setError(portalErrorMessage(caught, t("portals.could_not_publish_article")));
      setPublishing(null);
    } finally {
      setBusy(false);
    }
  }

  if (!portalId) return <ErrorScreen retry={openPortals} />;
  if (failed) return <ErrorScreen retry={() => void load()} />;
  if (!portal || !address) return <LoadingState />;

  // Редактор статьи занимает всю область раздела: шапки портала в нём нет.
  if (editing !== undefined) {
    return (
      <>
        <PortalArticleEditor
          article={editing}
          canManage={canManage && portal.status !== "ARCHIVED"}
          categories={categories}
          portal={portal}
          onClose={() => setEditing(undefined)}
          onPublish={(article, revisionId) => setPublishing({ article, revisionId })}
          onSaved={load}
        />
        <DecisionDialog
          open={publishing !== null}
          onClose={() => setPublishing(null)}
          tone="warning"
          icon="check"
          title={t("portals.publish_selected_version")}
          description={t("portals.version_will_become_available_portal")}
          actions={<>
            <Button variant="secondary" onClick={() => setPublishing(null)}>{t("common.cancel")}</Button>
            <Button variant="primary" disabled={busy} onClick={() => void publish()}>{t("common.publish")}</Button>
          </>}
        />
      </>
    );
  }

  return (
    <section className="portal-card">
      <PortalHeader
        canManage={canManage}
        portal={portal}
        settingsActive={section !== null}
        onOpenPortals={openPortals}
        onOpenContent={() => openPortalContent(portal.id)}
        onOpenSettings={() => (section === null ? openPortalSettings(portal.id) : openPortalContent(portal.id))}
        onCreateArticle={() => setEditing(null)}
        onChangeStatus={(status) => (status === "ARCHIVED" ? setPendingStatus(status) : void setStatus(status))}
      />

      {error && <div className="portal-form-error portal-card-error">{error}</div>}

      {section === null ? (
        <PortalLibrary
          canLinkAgents={hasCapability(user, "ai.manage")}
          canManage={canManage && portal.status !== "ARCHIVED"}
          categories={categories}
          portalId={portal.id}
          reload={load}
          onEditArticle={setEditing}
        />
      ) : (
        <PortalSettings
          address={address}
          canManage={canManage && portal.status !== "ARCHIVED"}
          portal={portal}
          section={section}
          onChanged={setPortal}
          openSection={(next) => openPortalSettings(portal.id, next)}
        />
      )}

      <DecisionDialog
        open={pendingStatus !== null}
        onClose={() => setPendingStatus(null)}
        tone="danger"
        icon="trash"
        title={t("portals.move_portal_archive")}
        description={t("portals.portal_its_material_become_unavailable")}
        actions={<>
          <Button variant="secondary" onClick={() => setPendingStatus(null)}>{t("common.cancel")}</Button>
          <Button variant="danger-outline" disabled={busy} onClick={() => pendingStatus && void setStatus(pendingStatus)}>{t("common.archive")}</Button>
        </>}
      />
    </section>
  );
}
