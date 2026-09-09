import { Dropdown } from "antd";
import { useCallback, useEffect, useMemo, useState } from "react";

import { hasCapability } from "../../auth/access";
import { Icon } from "../../shared/icons";
import { Pagination } from "../../shared/Pagination";
import { ErrorScreen, LoadingState, StatusPill } from "../../shared/ui";
import { Button, CopyButton, FilterDropdown, SearchInput } from "../../shared/ui-controls";
import { useDebounced } from "../../shared/useDebounced";
import { usePagedResource } from "../../shared/usePagedResource";
import type { SessionUser } from "../../types";
import {
  changePortalStatus,
  listSupportPortals,
  portalErrorMessage,
  PORTAL_STATUS_LABEL,
  type PortalAddressConfig,
  type PortalStatus,
  type SupportPortal,
} from "./model";
import {
  contentSummary,
  portalSubtitle,
  publicHost,
  updatedAt,
} from "./portalText";
import { PortalCreateDialog } from "./PortalCreateDialog";
import { DecisionDialog } from "../../shared/DecisionDialog";
import "./styles";
import { t, tn } from "../../i18n";

// Список порталов (дизайн-базлайн v2, кадры PT1/PT2). Адрес — колонка со
// ссылкой и копированием, действия строки — в меню ⋯, архивные приглушены и
// уходят в конец списка.

const STATUS_FILTER: Array<{ value: string; label: string }> = [
  { value: "PUBLISHED", label: PORTAL_STATUS_LABEL.PUBLISHED },
  { value: "DRAFT", label: PORTAL_STATUS_LABEL.DRAFT },
  { value: "ARCHIVED", label: PORTAL_STATUS_LABEL.ARCHIVED },
];

function pillStatus(status: PortalStatus): "published" | "archived" | "draft" {
  if (status === "PUBLISHED") return "published";
  if (status === "ARCHIVED") return "archived";
  return "draft";
}

export function SupportPortalsPage({
  user,
  openPortal,
  openPortalSettings,
}: {
  user: SessionUser;
  openPortal: (portalId: number) => void;
  openPortalSettings: (portalId: number) => void;
}) {
  const [address, setAddress] = useState<PortalAddressConfig | null>(null);
  const [failed, setFailed] = useState(false);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<string[]>([]);
  const [statusOpen, setStatusOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [archiving, setArchiving] = useState<SupportPortal | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const canManage = hasCapability(user, "support.operate");

  // Страницу, фильтр по статусу и поиск считает сервер: порталов может быть
  // сколько угодно, и резать список в браузере нельзя.
  const settledSearch = useDebounced(search);
  const query = useMemo(() => ({ status, search: settledSearch }), [settledSearch, status]);
  const loadPage = useCallback(async (page: number) => {
    const payload = await listSupportPortals(query, page);
    setAddress(payload.address);
    setFailed(false);
    return payload;
  }, [query]);
  const portals = usePagedResource(loadPage, query, t("portals.could_not_load_portals"));
  const load = portals.reload;


  async function archive(portal: SupportPortal) {
    setBusy(true);
    setError("");
    try {
      await changePortalStatus(portal.id, "ARCHIVED");
      setArchiving(null);
      await load();
    } catch (caught) {
      setError(portalErrorMessage(caught, t("portals.could_not_move_portal_archive")));
      setArchiving(null);
    } finally {
      setBusy(false);
    }
  }

  if (failed || portals.errorText) return <ErrorScreen retry={() => void load()} />;
  if (!address) return <LoadingState />;

  const createButton = canManage ? (
    <Button variant="primary" icon="plus" iconSize={16} onClick={() => setCreating(true)}>{t("portals.create_portal")}</Button>
  ) : null;

  const dialogs = (
    <>
      {creating && (
        <PortalCreateDialog
          open
          address={address}
          onClose={() => setCreating(false)}
          onCreated={(portal) => {
            setCreating(false);
            openPortal(portal.id);
          }}
        />
      )}
      <DecisionDialog
        open={archiving !== null}
        onClose={() => setArchiving(null)}
        tone="danger"
        icon="trash"
        title={t("portals.move_portal_archive")}
        description={t("portals.portal_its_material_become_unavailable")}
        actions={<>
          <Button variant="secondary" onClick={() => setArchiving(null)}>{t("common.cancel")}</Button>
          <Button variant="danger-outline" disabled={busy} onClick={() => archiving && void archive(archiving)}>{t("common.archive")}</Button>
        </>}
      />
    </>
  );

  // Пустое состояние — только когда порталов нет вовсе, а не когда их скрыл фильтр.
  if (portals.total === 0 && status.length === 0 && !settledSearch.trim()) {
    // Кадр PT2: создание доступно всегда, тарифных лимитов нет.
    return (
      <section className="portals-page is-empty">
        <header className="portals-head">
          <div>
            <h2>{t("common.portals")}</h2>
            <p>{t("portals.public_knowledge_bases_customers")}</p>
          </div>
          {createButton}
        </header>
        <div className="portals-empty">
          <div>
            <span className="portals-empty-mark"><Icon name="globe" size={27} strokeWidth={1.7} /></span>
            <h3>{t("portals.create_first_support_portal")}</h3>
            <p>{t("portals.portal_public_page_with_instructions")}</p>
            <div className="portals-empty-actions">
              {createButton}
              {/* Витрина посетителя — это и есть публичный help-контур установки:
                  открываем его базовый адрес, отдельного демо-экрана нет. */}
              <a
                className="secondary-button"
                href={`${address.scheme}://${address.baseDomain}${address.port ? `:${address.port}` : ""}/`}
                rel="noreferrer"
                target="_blank"
              >{t("portals.how_looks_customer")}</a>
            </div>
          </div>
        </div>
        {dialogs}
      </section>
    );
  }

  return (
    <section className="portals-page">
      <header className="portals-head">
        <div>
          <h2>{t("common.portals")}</h2>
          <p>{t("portals.public_knowledge_bases_customers_every")}</p>
        </div>
        {createButton}
      </header>

      {error && <div className="portal-form-error">{error}</div>}

      <div className="portals-card">
        <div className="portals-card-head">
          <SearchInput
            className="portals-search"
            placeholder={t("portals.search_by_name_address")}
            value={search}
            onChange={setSearch}
          />
          <FilterDropdown
            caption={t("portals.status")}
            label={status.length === 1 ? STATUS_FILTER.find((item) => item.value === status[0])!.label : t("common.all")}
            multiple
            open={statusOpen}
            options={STATUS_FILTER}
            selected={status}
            className="portals-status-filter"
            onOpenChange={setStatusOpen}
            onSelect={(value) => {
              setStatus((current) => (current.includes(value)
                ? current.filter((item) => item !== value)
                : [...current, value]));
            }}
          />
        </div>

        <table className="portals-table">
          <thead>
            <tr>
              <th>{t("portals.portal")}</th>
              <th>{t("portals.public_address")}</th>
              <th>{t("common.status_2")}</th>
              <th>{t("portals.material_2")}</th>
              <th>{t("portals.updated")}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {portals.items.map((portal) => {
              const host = publicHost(portal);
              const ownDomain = Boolean(portal.customDomain && portal.customDomainVerifiedAt);
              const archived = portal.status === "ARCHIVED";
              const menuItems = [
                { key: "content", label: <button type="button" onClick={() => openPortal(portal.id)}><Icon name="folder" size={15} strokeWidth={1.9} />{t("portals.open_material")}</button> },
                { key: "settings", label: <button type="button" onClick={() => openPortalSettings(portal.id)}><Icon name="settings" size={15} strokeWidth={1.9} />{t("shared.portal_settings")}</button> },
                { key: "divider-1", type: "divider" as const },
                { key: "copy", label: <button type="button" onClick={() => void navigator.clipboard?.writeText(portal.publicUrl)}><Icon name="copy" size={15} strokeWidth={1.9} />{t("portals.copy_public_link")}</button> },
                { key: "open", label: <button type="button" onClick={() => window.open(portal.publicUrl, "_blank", "noreferrer")}><Icon name="external" size={15} strokeWidth={1.9} />{t("portals.open_portal")}</button> },
                ...(canManage && !archived ? [
                  { key: "divider-2", type: "divider" as const },
                  { key: "archive", label: <button className="danger" type="button" onClick={() => setArchiving(portal)}><Icon name="trash" size={15} strokeWidth={1.9} />{t("common.move_archive")}</button> },
                ] : []),
              ];
              return (
                <tr className={`portals-row${archived ? " is-archived" : ""}`} key={portal.id} onClick={() => openPortal(portal.id)}>
                  <td>
                    <span className="portals-name">
                      <i className={ownDomain || portal.status === "PUBLISHED" ? "is-live" : ""}><Icon name="globe" size={18} strokeWidth={1.8} /></i>
                      <span>
                        <strong>{portal.name}</strong>
                        <small>{portalSubtitle(portal)}</small>
                      </span>
                    </span>
                  </td>
                  <td onClick={(event) => event.stopPropagation()}>
                    <span className="portals-address">
                      <code>{host}</code>
                      <CopyButton className="portals-copy" label="" value={portal.publicUrl} />
                      {ownDomain && (
                        <small className="portals-domain-badge">
                          <Icon name="check" size={11} strokeWidth={2.6} />{t("portals.custom_domain_2")}</small>
                      )}
                    </span>
                  </td>
                  <td><StatusPill status={pillStatus(portal.status)} label={PORTAL_STATUS_LABEL[portal.status]} /></td>
                  <td className="portals-content-cell">{contentSummary(portal)}</td>
                  <td className="portals-updated-cell">{updatedAt(portal.updatedAt)}</td>
                  <td className="row-actions" onClick={(event) => event.stopPropagation()}>
                    <Dropdown menu={{ items: menuItems }} overlayClassName="app-dropdown is-portal-menu" placement="bottomRight" trigger={["click"]}>
                      <button aria-label={t("common.actions_for", { name: portal.name })} className="row-menu-button" type="button"><Icon name="more" size={16} strokeWidth={2} /></button>
                    </Dropdown>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        <Pagination
          note={t("portals.portals_note", { count: tn("plural.portals", portals.total) })}
          page={portals.page}
          pageCount={portals.pageCount}
          onPage={portals.setPage}
        />
      </div>
      {dialogs}
    </section>
  );
}
