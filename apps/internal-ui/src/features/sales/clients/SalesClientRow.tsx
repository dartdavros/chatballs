import { Dropdown } from "antd";

import { Icon } from "../../../shared/icons";
import type { SalesClientRowVm } from "./model";

export function SalesClientRow({ client, menu, openClient, setMenu }: { client: SalesClientRowVm; menu: string | null; openClient: (id: number) => void; setMenu: (menu: string | null) => void }) {
  const menuOpen = menu === client.cid;
  const menuItems = [
    { key: "open", label: <button type="button" onClick={() => { setMenu(null); openClient(client.id); }}><Icon name="external" size={15} />Открыть клиента</button> },
    { key: "merge", label: <button type="button"><Icon name="list" size={15} />Объединить контакты</button> },
    { type: "divider" as const },
    { key: "anonymize", label: <button className="danger" type="button"><Icon name="eyeOff" size={15} />Обезличить данные</button> },
  ];
  return (
    <tr>
      <td>
        <div className="sales-client-person">
          <div style={{ background: client.avatarBg }}>{client.initials}</div>
          <span>
            <button className="link" type="button" onClick={() => openClient(client.id)}>{client.name}</button>
            <small>{client.cid}</small>
          </span>
        </div>
      </td>
      <td>
        <span className="sales-client-status" style={{ background: client.statusMeta.bg, color: client.statusMeta.color }}>{client.statusMeta.label}</span>
      </td>
      <td>
        <div className={`sales-client-contact ${client.phone ? "" : "muted"}`}>{client.phone || "—"}</div>
        <small className="sales-client-phone">{client.username ? `@${client.username}` : ""}</small>
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
        <Dropdown menu={{ items: menuItems }} open={menuOpen} onOpenChange={(open) => setMenu(open ? client.cid : null)} trigger={["click"]} overlayClassName="app-dropdown is-wide">
          <button className="row-menu-button" type="button" aria-label="Действия клиента"><Icon name="more" /></button>
        </Dropdown>
      </td>
    </tr>
  );
}
