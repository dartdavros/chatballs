import type { MouseEvent } from "react";

import { Icon } from "../../../shared/icons";
import type { SalesClientRowVm } from "./model";

export function SalesClientRow({ client, menu, setMenu }: { client: SalesClientRowVm; menu: { id: string; left: number; top: number } | null; setMenu: (menu: { id: string; left: number; top: number } | null) => void }) {
  const menuOpen = menu?.id === client.cid;
  function toggleMenu(event: MouseEvent<HTMLButtonElement>) {
    if (menuOpen) {
      setMenu(null);
      return;
    }
    const rect = event.currentTarget.getBoundingClientRect();
    setMenu({ id: client.cid, left: Math.max(8, rect.right - 212), top: rect.bottom + 6 });
  }
  return (
    <tr>
      <td>
        <div className="sales-client-person">
          <div style={{ background: client.avatarBg }}>{client.initials}</div>
          <span>
            <a href="#" onClick={(event) => event.preventDefault()}>{client.name}</a>
            <small>{client.cid}</small>
          </span>
        </div>
      </td>
      <td>
        <div className={`sales-client-contact ${client.anon ? "muted" : ""}`}>{client.email}</div>
        <small className="sales-client-phone">{client.phone}</small>
      </td>
      <td>
        <div className="sales-client-tags">
          {client.channels.map((channel) => (
            <span style={{ background: channel.bg }} title={channel.full} key={channel.label}><i style={{ background: channel.color }} /><b style={{ color: channel.color }}>{channel.label}</b></span>
          ))}
        </div>
      </td>
      <td>
        <div className="sales-client-products">
          {client.products.map((product) => <span style={{ background: product.bg, color: product.color }} key={product.name}>{product.name}</span>)}
        </div>
      </td>
      <td><div className="sales-client-last"><i style={{ background: client.lastDot }} />{client.lastLabel}</div></td>
      <td className="numeric"><strong style={{ color: client.openColor }}>{client.openDialogs}</strong></td>
      <td className="numeric">{client.orders}</td>
      <td className="numeric"><strong style={{ color: client.totalColor }}>{client.totalLabel}</strong></td>
      <td className="row-actions">
        <button className="row-menu-button" type="button" aria-label="Действия клиента" onClick={toggleMenu}><Icon name="more" /></button>
        {menuOpen && (
          <div className="row-menu sales-client-row-menu" style={{ left: menu.left, position: "fixed", right: "auto", top: menu.top }}>
            <a href="#" onClick={(event) => event.preventDefault()}><Icon name="external" size={15} />Открыть клиента</a>
            <a href="#" onClick={(event) => event.preventDefault()}><Icon name="list" size={15} />Объединить контакты</a>
            <span />
            <a className="danger" href="#" onClick={(event) => event.preventDefault()}><Icon name="eyeOff" size={15} />Обезличить данные</a>
          </div>
        )}
      </td>
    </tr>
  );
}
