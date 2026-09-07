import { Dropdown } from "antd";
import { useCallback, useEffect, useMemo, useState } from "react";

import { hasCapability } from "../../auth/access";
import { Icon } from "../../shared/icons";
import { ErrorScreen, LoadingState, StatusPill } from "../../shared/ui";
import { Button, CopyButton, FilterDropdown, SearchInput } from "../../shared/ui-controls";
import { pluralRu } from "../../shared/utils";
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
  productsSummary,
  publicHost,
  updatedAt,
} from "./portalText";
import { PortalCreateDialog } from "./PortalCreateDialog";
import { PortalTableFooter } from "./PortalTableFooter";
import { DecisionDialog } from "../../shared/DecisionDialog";
import "./styles";

// Список порталов (дизайн-базлайн v2, кадры PT1/PT2). Адрес — колонка со
// ссылкой и копированием, действия строки — в меню ⋯, архивные приглушены и
// уходят в конец списка.

const PAGE_SIZE = 20;

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
  const [portals, setPortals] = useState<SupportPortal[] | null>(null);
  const [address, setAddress] = useState<PortalAddressConfig | null>(null);
  const [failed, setFailed] = useState(false);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<string[]>([]);
  const [statusOpen, setStatusOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [creating, setCreating] = useState(false);
  const [archiving, setArchiving] = useState<SupportPortal | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const canManage = hasCapability(user, "support.operate");

  const load = useCallback(async () => {
    setFailed(false);
    try {
      const payload = await listSupportPortals();
      setPortals(payload.items);
      setAddress(payload.address);
    } catch {
      setFailed(true);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    return (portals ?? [])
      .filter((portal) => (
        (status.length === 0 || status.includes(portal.status))
        && (!query
          || portal.name.toLocaleLowerCase().includes(query)
          || publicHost(portal).toLocaleLowerCase().includes(query))
      ))
      // Архивные показываются последними (подпись в подвале кадра PT1).
      .sort((left, right) => Number(left.status === "ARCHIVED") - Number(right.status === "ARCHIVED"));
  }, [portals, search, status]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount);
  const visible = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  async function archive(portal: SupportPortal) {
    setBusy(true);
    setError("");
    try {
      await changePortalStatus(portal.id, "ARCHIVED");
      setArchiving(null);
      await load();
    } catch (caught) {
      setError(portalErrorMessage(caught, "Не удалось перенести портал в архив"));
      setArchiving(null);
    } finally {
      setBusy(false);
    }
  }

  if (failed) return <ErrorScreen retry={() => void load()} />;
  if (!portals || !address) return <LoadingState />;

  const createButton = canManage ? (
    <Button variant="primary" icon="plus" iconSize={16} onClick={() => setCreating(true)}>
      Создать портал
    </Button>
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
        title="Перенести портал в архив?"
        description="Портал и его материалы станут недоступны посетителям до восстановления."
        actions={<>
          <Button variant="secondary" onClick={() => setArchiving(null)}>Отмена</Button>
          <Button variant="danger-outline" disabled={busy} onClick={() => archiving && void archive(archiving)}>В архив</Button>
        </>}
      />
    </>
  );

  if (portals.length === 0) {
    // Кадр PT2: создание доступно всегда, тарифных лимитов нет.
    return (
      <section className="portals-page is-empty">
        <header className="portals-head">
          <div>
            <h2>Порталы</h2>
            <p>Публичные базы знаний для клиентов.</p>
          </div>
          {createButton}
        </header>
        <div className="portals-empty">
          <div>
            <span className="portals-empty-mark"><Icon name="globe" size={27} strokeWidth={1.7} /></span>
            <h3>Создайте первый портал поддержки</h3>
            <p>Портал — публичная страница с инструкциями и ответами на частые вопросы. Клиент читает статью и, если не нашёл ответ, пишет в чат прямо со страницы.</p>
            <div className="portals-empty-actions">
              {createButton}
              {/* Витрина посетителя — это и есть публичный help-контур установки:
                  открываем его базовый адрес, отдельного демо-экрана нет. */}
              <a
                className="secondary-button"
                href={`${address.scheme}://${address.baseDomain}${address.port ? `:${address.port}` : ""}/`}
                rel="noreferrer"
                target="_blank"
              >
                Как это выглядит у клиента
              </a>
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
          <h2>Порталы</h2>
          <p>Публичные базы знаний для клиентов. Каждый портал — свой адрес, оформление и материалы.</p>
        </div>
        {createButton}
      </header>

      {error && <div className="portal-form-error">{error}</div>}

      <div className="portals-card">
        <div className="portals-card-head">
          <SearchInput
            className="portals-search"
            placeholder="Поиск по названию и адресу"
            value={search}
            onChange={(value) => { setSearch(value); setPage(1); }}
          />
          <FilterDropdown
            caption="Статус:"
            label={status.length === 1 ? STATUS_FILTER.find((item) => item.value === status[0])!.label : "Все"}
            multiple
            open={statusOpen}
            options={STATUS_FILTER}
            selected={status}
            className="portals-status-filter"
            onOpenChange={setStatusOpen}
            onSelect={(value) => {
              setPage(1);
              setStatus((current) => (current.includes(value)
                ? current.filter((item) => item !== value)
                : [...current, value]));
            }}
          />
        </div>

        <table className="portals-table">
          <thead>
            <tr>
              <th>ПОРТАЛ</th>
              <th>ПУБЛИЧНЫЙ АДРЕС</th>
              <th>СТАТУС</th>
              <th>МАТЕРИАЛЫ</th>
              <th>ПРОДУКТЫ</th>
              <th>ОБНОВЛЁН</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {visible.map((portal) => {
              const host = publicHost(portal);
              const ownDomain = Boolean(portal.customDomain && portal.customDomainVerifiedAt);
              const archived = portal.status === "ARCHIVED";
              const menuItems = [
                { key: "content", label: <button type="button" onClick={() => openPortal(portal.id)}><Icon name="folder" size={15} strokeWidth={1.9} />Открыть материалы</button> },
                { key: "settings", label: <button type="button" onClick={() => openPortalSettings(portal.id)}><Icon name="settings" size={15} strokeWidth={1.9} />Настройки портала</button> },
                { key: "divider-1", type: "divider" as const },
                { key: "copy", label: <button type="button" onClick={() => void navigator.clipboard?.writeText(portal.publicUrl)}><Icon name="copy" size={15} strokeWidth={1.9} />Копировать публичную ссылку</button> },
                { key: "open", label: <button type="button" onClick={() => window.open(portal.publicUrl, "_blank", "noreferrer")}><Icon name="external" size={15} strokeWidth={1.9} />Открыть портал</button> },
                ...(canManage && !archived ? [
                  { key: "divider-2", type: "divider" as const },
                  { key: "archive", label: <button className="danger" type="button" onClick={() => setArchiving(portal)}><Icon name="trash" size={15} strokeWidth={1.9} />Перенести в архив</button> },
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
                          <Icon name="check" size={11} strokeWidth={2.6} />свой домен
                        </small>
                      )}
                    </span>
                  </td>
                  <td><StatusPill status={pillStatus(portal.status)} label={PORTAL_STATUS_LABEL[portal.status]} /></td>
                  <td className="portals-content-cell">{contentSummary(portal)}</td>
                  <td className="portals-products-cell">{productsSummary(portal)}</td>
                  <td className="portals-updated-cell">{updatedAt(portal.updatedAt)}</td>
                  <td className="row-actions" onClick={(event) => event.stopPropagation()}>
                    <Dropdown menu={{ items: menuItems }} overlayClassName="app-dropdown is-portal-menu" placement="bottomRight" trigger={["click"]}>
                      <button aria-label={`Действия: ${portal.name}`} className="row-menu-button" type="button"><Icon name="more" size={16} strokeWidth={2} /></button>
                    </Dropdown>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        <PortalTableFooter
          note={`${pluralRu(filtered.length, ["портал", "портала", "порталов"])} · архивные показываются последними`}
          page={currentPage}
          pageCount={pageCount}
          onPageChange={setPage}
        />
      </div>
      {dialogs}
    </section>
  );
}
