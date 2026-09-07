import { Dropdown } from "antd";

import { Icon } from "../../shared/icons";
import { StatusPill } from "../../shared/ui";
import { Button, CopyButton } from "../../shared/ui-controls";
import { PORTAL_STATUS_LABEL, type PortalStatus, type SupportPortal } from "./model";
import { contentSummary, hostedHost, localeName, publicHost } from "./portalText";

// Шапка карточки портала (дизайн-базлайн v2, кадр PT3): публичный адрес —
// постоянный элемент, а не текст в подзаголовке: копирование, открытие,
// состояние домена и резервный адрес установки видны всегда, включая черновик.

function pillStatus(status: PortalStatus): "published" | "archived" | "draft" {
  if (status === "PUBLISHED") return "published";
  if (status === "ARCHIVED") return "archived";
  return "draft";
}

export function PortalHeader({
  portal,
  canManage,
  settingsActive,
  onOpenPortals,
  onOpenContent,
  onOpenSettings,
  onCreateArticle,
  onChangeStatus,
}: {
  portal: SupportPortal;
  canManage: boolean;
  settingsActive: boolean;
  onOpenPortals: () => void;
  onOpenContent: () => void;
  onOpenSettings: () => void;
  onCreateArticle: () => void;
  onChangeStatus: (status: PortalStatus) => void;
}) {
  const ownDomain = Boolean(portal.customDomain);
  const domainLive = ownDomain && Boolean(portal.customDomainVerifiedAt);
  const archived = portal.status === "ARCHIVED";
  const menuItems = [
    ...(canManage && portal.status === "DRAFT" ? [{
      key: "publish",
      label: <button type="button" onClick={() => onChangeStatus("PUBLISHED")}><Icon name="check" size={15} strokeWidth={2.2} />Опубликовать портал</button>,
    }] : []),
    ...(canManage && portal.status === "PUBLISHED" ? [{
      key: "unpublish",
      label: <button type="button" onClick={() => onChangeStatus("DRAFT")}><Icon name="undo" size={15} strokeWidth={1.9} />Снять с публикации</button>,
    }] : []),
    ...(canManage && archived ? [{
      key: "restore",
      label: <button type="button" onClick={() => onChangeStatus("DRAFT")}><Icon name="undo" size={15} strokeWidth={1.9} />Вернуть из архива</button>,
    }] : []),
    { key: "open", label: <button type="button" onClick={() => window.open(portal.publicUrl, "_blank", "noreferrer")}><Icon name="external" size={15} strokeWidth={1.9} />Открыть портал</button> },
    ...(canManage && !archived ? [
      { key: "divider", type: "divider" as const },
      { key: "archive", label: <button className="danger" type="button" onClick={() => onChangeStatus("ARCHIVED")}><Icon name="trash" size={15} strokeWidth={1.9} />Перенести в архив</button> },
    ] : []),
  ];

  return (
    <div className="portal-card-head">
      <div className="portal-card-head-inner">
        <nav className="portal-breadcrumbs">
          <button className="link is-strong" type="button" onClick={onOpenPortals}>Порталы</button>
          <span>/</span>
          {settingsActive
            ? <><button className="link is-muted" type="button" onClick={onOpenContent}>{portal.name}</button><span>/</span><b>Настройки</b></>
            : <span>{portal.name}</span>}
        </nav>

        <div className="portal-card-head-row">
          <div className="portal-card-identity">
            <div className="portal-card-title">
              <h2>{portal.name}</h2>
              <StatusPill status={pillStatus(portal.status)} label={PORTAL_STATUS_LABEL[portal.status]} />
              <span>{contentSummary(portal)} · {localeName(portal.defaultLocale)}</span>
            </div>

            <div className="portal-address-row">
              <span className={`portal-address-chip${domainLive ? " is-live" : ""}`}>
                <Icon name="globe" size={15} strokeWidth={1.9} />
                <code>{publicHost(portal)}</code>
                {ownDomain && (
                  <span className={`portal-domain-tag${domainLive ? "" : " is-pending"}`}>
                    свой домен · {domainLive ? "работает" : "не проверен"}
                  </span>
                )}
                <CopyButton className="portal-address-copy" label="" value={portal.publicUrl} />
                <a
                  className="portal-address-open"
                  href={portal.publicUrl}
                  rel="noreferrer"
                  target="_blank"
                  title="Открыть портал в новой вкладке"
                >
                  <Icon name="external" size={14} strokeWidth={2} />
                </a>
              </span>
              {ownDomain && (
                <span className="portal-hosted-note">
                  адрес на этой установке <code>{hostedHost(portal)}</code>
                </span>
              )}
            </div>
          </div>

          <div className="portal-card-actions">
            <button
              className={`portal-settings-button${settingsActive ? " is-active" : ""}`}
              type="button"
              onClick={onOpenSettings}
            >
              <Icon name="settings" size={15} strokeWidth={1.9} />Настройки
            </button>
            {canManage && !archived && (
              <Button variant="primary" className="portal-primary-action" icon="plus" onClick={onCreateArticle}>
                Новая статья
              </Button>
            )}
            <Dropdown menu={{ items: menuItems }} overlayClassName="app-dropdown is-portal-menu" placement="bottomRight" trigger={["click"]}>
              <button aria-label="Ещё" className="portal-more-button" title="Ещё" type="button">
                <Icon name="more" size={16} strokeWidth={2} />
              </button>
            </Dropdown>
          </div>
        </div>
      </div>
    </div>
  );
}
