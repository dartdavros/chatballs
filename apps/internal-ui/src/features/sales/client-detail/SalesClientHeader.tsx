import { useState } from "react";

import { Icon } from "../../../shared/icons";
import { Button } from "../../../shared/ui-controls";
import type { RouteKey } from "../../../types";
import type { ClientDetailVm } from "./model";

export function SalesClientHeader({ client, setRoute }: { client: ClientDetailVm; setRoute: (route: RouteKey) => void }) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="sales-client-detail-header-card">
      {menuOpen && <button className="sales-client-detail-scrim" type="button" aria-label="Закрыть меню" onClick={() => setMenuOpen(false)} />}
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
          <button className={`sales-client-more ${menuOpen ? "active" : ""}`} type="button" aria-label="Действия клиента" onClick={() => setMenuOpen((value) => !value)}><Icon name="more" size={18} /></button>
          {menuOpen && <SalesClientMenu />}
        </div>
      </div>
    </div>
  );
}

function SalesClientMenu() {
  return (
    <div className="sales-client-detail-menu">
      <a href="#" onClick={(event) => event.preventDefault()}><Icon name="list" size={15} />Объединить контакты</a>
      <a href="#" onClick={(event) => event.preventDefault()}><Icon name="split" size={15} />Разъединить контакты</a>
      <a href="#" onClick={(event) => event.preventDefault()}><Icon name="edit" size={15} />Исправить данные</a>
      <span />
      <a className="danger" href="#" onClick={(event) => event.preventDefault()}><Icon name="eyeOff" size={15} />Обезличить данные</a>
    </div>
  );
}
