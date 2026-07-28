import { Modal } from "antd";
import { useCallback, useEffect, useState } from "react";

import { hasCapability } from "../../auth/access";
import { DecisionDialog } from "../../shared/DecisionDialog";
import { ErrorScreen, LoadingState, PageHeader, StatusPill } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import type { Product, SessionUser } from "../../types";
import {
  changePortalStatus,
  listPortalArticles,
  listPortalCategories,
  loadSupportPortal,
  portalErrorMessage,
  type PortalArticle,
  type PortalCategory,
  type SupportPortal,
} from "./model";
import { PortalContent } from "./PortalContent";
import { PortalSettings } from "./PortalSettings";
import "./styles";

export function SupportPortalDetailPage({
  portalId,
  products,
  user,
  openPortals,
}: {
  portalId: number | null;
  products: Product[];
  user: SessionUser;
  openPortals: () => void;
}) {
  const [portal, setPortal] = useState<SupportPortal | null>(null);
  const [categories, setCategories] = useState<PortalCategory[]>([]);
  const [articles, setArticles] = useState<PortalArticle[]>([]);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [pendingStatus, setPendingStatus] = useState<"DRAFT" | "PUBLISHED" | "ARCHIVED" | null>(null);
  const [actionError, setActionError] = useState("");
  const canManage = hasCapability(user, "support.operate", "support");

  const load = useCallback(async () => {
    if (!portalId) return;
    setFailed(false);
    try {
      const [portalPayload, categoryPayload, articlePayload] = await Promise.all([
        loadSupportPortal(portalId),
        listPortalCategories(portalId),
        listPortalArticles(portalId),
      ]);
      setPortal(portalPayload.portal);
      setCategories(categoryPayload.items);
      setArticles(articlePayload.items);
    } catch {
      setFailed(true);
    }
  }, [portalId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function setStatus(status: "DRAFT" | "PUBLISHED" | "ARCHIVED") {
    if (!portal) return;
    setBusy(true);
    setActionError("");
    try {
      const payload = await changePortalStatus(portal.id, status);
      setPortal(payload.portal);
      setPendingStatus(null);
    } catch (caught) {
      setActionError(portalErrorMessage(caught, "Не удалось изменить статус портала"));
    } finally {
      setBusy(false);
    }
  }

  if (!portalId) return <ErrorScreen retry={openPortals} />;
  if (failed) return <ErrorScreen retry={() => void load()} />;
  if (!portal) return <LoadingState />;

  const action = portal.status === "PUBLISHED" || canManage ? (
    <div className="portal-header-actions">
      {portal.status === "PUBLISHED" && <a className="link has-icon" href={portal.publicUrl} target="_blank" rel="noreferrer">Открыть портал</a>}
      {canManage && <Button variant="secondary" icon="settings" onClick={() => setSettingsOpen(true)}>Настройки</Button>}
      {canManage && portal.status !== "PUBLISHED" && portal.status !== "ARCHIVED" && <Button variant="primary" disabled={busy} onClick={() => setPendingStatus("PUBLISHED")}>Опубликовать</Button>}
      {canManage && portal.status === "ARCHIVED" && <Button variant="secondary" disabled={busy} onClick={() => void setStatus("DRAFT")}>Вернуть из архива</Button>}
      {canManage && portal.status !== "ARCHIVED" && <Button variant="secondary" disabled={busy} onClick={() => setPendingStatus("ARCHIVED")}>В архив</Button>}
    </div>
  ) : undefined;

  return (
    <div className="support-portal-detail">
      <PageHeader
        title={portal.name}
        text={<span><StatusPill status={portal.status === "PUBLISHED" ? "published" : portal.status === "ARCHIVED" ? "archived" : "draft"} /><code>{portal.publicUrl}</code></span>}
        action={action}
      />
      <PortalContent
        articles={articles}
        canManage={canManage && portal.status !== "ARCHIVED"}
        categories={categories}
        locale={portal.defaultLocale}
        portalId={portal.id}
        reload={load}
      />
      <Modal
        destroyOnHidden
        footer={null}
        open={settingsOpen}
        title="Настройки портала"
        width={960}
        onCancel={() => setSettingsOpen(false)}
      >
        <PortalSettings portal={portal} products={products} canManage={canManage && portal.status !== "ARCHIVED"} onChanged={setPortal} />
      </Modal>
      {actionError && <div className="portal-form-error">{actionError}</div>}
      <DecisionDialog
        open={pendingStatus !== null}
        onClose={() => setPendingStatus(null)}
        tone={pendingStatus === "ARCHIVED" ? "danger" : "warning"}
        icon={pendingStatus === "ARCHIVED" ? "trash" : "check"}
        title={pendingStatus === "ARCHIVED" ? "Перенести портал в архив?" : "Опубликовать портал?"}
        description={pendingStatus === "ARCHIVED"
          ? "Портал и его материалы станут недоступны посетителям до восстановления."
          : "Опубликованные статьи станут доступны по публичному адресу."}
        actions={<><Button variant="secondary" onClick={() => setPendingStatus(null)}>Отмена</Button><Button variant={pendingStatus === "ARCHIVED" ? "danger-outline" : "primary"} disabled={busy} onClick={() => pendingStatus && void setStatus(pendingStatus)}>{pendingStatus === "ARCHIVED" ? "В архив" : "Опубликовать"}</Button></>}
      />
    </div>
  );
}
