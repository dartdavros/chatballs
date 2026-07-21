import { Dropdown } from "antd";
import { useState } from "react";

import { Icon } from "../../../shared/icons";
import { Button } from "../../../shared/ui-controls";
import type { RouteKey } from "../../../types";
import type { ClientDetailVm } from "./model";

export function SalesClientHeader({ client, setRoute }: { client: ClientDetailVm; setRoute: (route: RouteKey) => void }) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="sales-client-detail-header-card">
      <div className="sales-client-detail-header">
        <div className="sales-client-detail-avatar" style={{ background: client.avatarBg }}>{client.initials}</div>
        <div className="sales-client-detail-title">
          <div className="sales-client-detail-name-row">
            <h1>{client.name}</h1>
            <span className="sales-client-cid">{client.cid}</span>
          </div>
          <div className="sales-client-detail-meta">
            <span><Icon name="mail" size={14} /><b>{client.email}</b></span>
            <span><Icon name="phone" size={14} /><b className="muted">{client.phone}</b></span>
            <span className="sales-client-detail-channels">
              {client.channels.map((channel) => (
                <i style={{ background: channel.bg }} key={channel.label}><em style={{ background: channel.color }} /><b style={{ color: channel.color }}>{channel.label}</b></i>
              ))}
            </span>
          </div>
        </div>
        <div className="sales-client-detail-actions">
          <Button className="sales-client-primary" icon="message" variant="primary" onClick={() => setRoute("salesDialogs")}>Открыть диалог</Button>
          <Dropdown menu={{ items: clientMenuItems }} open={menuOpen} onOpenChange={setMenuOpen} trigger={["click"]} placement="bottomRight" overlayClassName="app-dropdown is-wide">
            <button className="row-menu-button" type="button" aria-label="Действия контакта"><Icon name="more" size={18} /></button>
          </Dropdown>
        </div>
      </div>
    </div>
  );
}

const clientMenuItems = [
  { key: "merge", label: <button type="button"><Icon name="list" size={15} />Объединить контакты</button> },
  { key: "split", label: <button type="button"><Icon name="split" size={15} />Разъединить контакты</button> },
  { key: "edit", label: <button type="button"><Icon name="edit" size={15} />Исправить данные</button> },
  { type: "divider" as const },
  { key: "anonymize", label: <button className="danger" type="button"><Icon name="eyeOff" size={15} />Обезличить данные</button> },
];
