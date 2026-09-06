import { useCallback, useEffect, useMemo, useState } from "react";

import { hasCapability } from "../../auth/access";
import { ContentLibraryTable } from "../../shared/content-library/ContentLibraryTable";
import { ContentLibraryToolbar } from "../../shared/content-library/ContentLibraryToolbar";
import { Icon } from "../../shared/icons";
import { ContentState, ErrorScreen, LoadingState, PageHeader, StatusPill } from "../../shared/ui";
import { Button } from "../../shared/ui-controls";
import { pluralRu } from "../../shared/utils";
import type { SessionUser } from "../../types";
import {
  listSupportPortals,
  type PortalAddressConfig,
  type SupportPortal,
} from "./model";
import { PortalCreateDialog } from "./PortalCreateDialog";
import "./styles";

export function SupportPortalsPage({
  user,
  openPortal,
}: {
  user: SessionUser;
  openPortal: (portalId: number) => void;
}) {
  const [portals, setPortals] = useState<SupportPortal[] | null>(null);
  const [address, setAddress] = useState<PortalAddressConfig | null>(null);
  const [failed, setFailed] = useState(false);
  const [search, setSearch] = useState("");
  const [creating, setCreating] = useState(false);
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
    if (!query) return portals ?? [];
    return (portals ?? []).filter((portal) => (
      portal.name.toLocaleLowerCase().includes(query)
      || portal.slug.toLocaleLowerCase().includes(query)
    ));
  }, [portals, search]);

  if (failed) return <ErrorScreen retry={() => void load()} />;
  if (!portals || !address) return <LoadingState />;

  const createAction = canManage ? (
    <Button variant="primary" icon="plus" onClick={() => setCreating(true)}>
      Создать портал
    </Button>
  ) : undefined;

  return (
    <div className="support-portals-page">
      <PageHeader
        title="Порталы"
        text="Публичные базы знаний для клиентов"
        action={createAction}
      />
      {portals.length === 0 ? (
        <ContentState
          icon={<Icon name="folder" size={24} />}
          title="Создайте первый портал поддержки"
          text="Публикуйте инструкции и ответы на частые вопросы для клиентов."
          action={createAction}
        />
      ) : (
        <div className="knowledge-library-list">
            <ContentLibraryToolbar
              placeholder="Поиск по названию и адресу"
              query={search}
              onQueryChange={setSearch}
            />
            <ContentLibraryTable
              emptyTitle="Порталы не найдены"
              error={false}
              errorTitle="Не удалось загрузить порталы"
              hasItems={filtered.length > 0}
              loading={false}
              onRetry={() => void load()}
              footer={<div className="ai-table-footer"><span>{pluralRu(filtered.length, ["портал", "портала", "порталов"])}</span></div>}
            >
              <table className="baseline-table knowledge-table">
              <thead><tr><th>ПОРТАЛ</th><th>СТАТУС</th><th>ПРОДУКТЫ</th><th /></tr></thead>
              <tbody>
                {filtered.map((portal) => (
                  <tr className="knowledge-row" key={portal.id} onClick={() => openPortal(portal.id)}>
                    <td>
                      <span className="support-portal-name">
                        <i><Icon name="folder" size={19} /></i>
                        <span>
                          <button className="link is-strong is-neutral" type="button" onClick={() => openPortal(portal.id)}>{portal.name}</button>
                          <small>{portal.publicUrl}</small>
                        </span>
                      </span>
                    </td>
                    <td><StatusPill status={portal.status === "PUBLISHED" ? "published" : portal.status === "ARCHIVED" ? "archived" : "draft"} /></td>
                    <td>{portal.products.length || "—"}</td>
                    <td className="support-portal-open"><Icon name="arrow" size={16} /></td>
                  </tr>
                ))}
              </tbody>
              </table>
          </ContentLibraryTable>
        </div>
      )}
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
    </div>
  );
}
