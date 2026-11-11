import { Dropdown } from "antd";
import { useState } from "react";

import { t } from "../../../../i18n";
import { Icon } from "../../../../shared/icons";
import { StatusPill } from "../../../../shared/ui";
import { connectionBadge } from "../model";
import { ServiceLogo } from "../ServiceLogo";
import type { ServiceAdapter, ServiceConnection } from "../types";

/** Шапка карточки: «‹ Сервисы», название, состояние, хост и меню действий. */
export function ServiceCardHeader({ connection, adapter, onBack, onToggleActive, onDelete }: {
  connection: ServiceConnection;
  adapter: ServiceAdapter | undefined;
  onBack: () => void;
  onToggleActive: () => void;
  onDelete: () => void;
}) {
  const [open, setOpen] = useState(false);
  const badge = connectionBadge(connection);
  const items = [
    {
      key: "active",
      label: (
        <button type="button" className={connection.isActive ? "warning" : ""} onClick={() => { setOpen(false); onToggleActive(); }}>
          <Icon name={connection.isActive ? "pause" : "play"} size={15} />{connection.isActive ? t("services.pause") : t("services.resume")}
        </button>
      ),
    },
    { type: "divider" as const },
    {
      key: "delete",
      label: <button type="button" className="danger" onClick={() => { setOpen(false); onDelete(); }}><Icon name="trash" size={15} />{t("services.delete_connection")}</button>,
    },
  ];
  return (
    <>
      <button className="link is-muted has-icon service-card-back" type="button" onClick={onBack}><Icon name="chevronLeft" size={14} strokeWidth={2.2} />{t("common.integrations")}</button>
      <header className="service-card-head">
        <div>
          <div className="service-card-title"><h2>{connection.name}</h2><StatusPill status={badge.status} label={badge.label} /></div>
          <p>{[adapter?.title, connection.host].filter(Boolean).join(" · ")}</p>
        </div>
        <div className="service-card-tools">
          {adapter && <ServiceLogo adapter={adapter} height={22} />}
          <Dropdown menu={{ items }} open={open} onOpenChange={setOpen} trigger={["click"]} overlayClassName="app-dropdown">
            <button className="row-menu-button" type="button" title={t("services.menu")} aria-label={t("services.menu")}><Icon name="more" /></button>
          </Dropdown>
        </div>
      </header>
    </>
  );
}
