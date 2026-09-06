import { Dropdown } from "antd";

import { ChannelGlyph } from "../../../shared/badges";
import { Icon } from "../../../shared/icons";
import { ContactAvatar } from "../../conversations/ContactAvatar";
import type { SalesClientRowVm } from "./model";

// Строка контакта (кадр K1). Вся строка кликабельна — открывает карточку.
export function SalesClientRow({ client, menu, openClient, setMenu }: { client: SalesClientRowVm; menu: string | null; openClient: (id: number) => void; setMenu: (menu: string | null) => void }) {
  const menuOpen = menu === client.cid;
  const menuItems = [
    { key: "open", label: <button type="button" onClick={() => { setMenu(null); openClient(client.id); }}><Icon name="external" size={15} />Открыть карточку</button> },
  ];
  return (
    <div className="sales-client-row" role="button" tabIndex={0} onClick={() => openClient(client.id)} onKeyDown={(event) => { if (event.key === "Enter") openClient(client.id); }}>
      <div className="sales-client-person">
        <ContactAvatar avatarUrl={client.avatarUrl || undefined} initials={client.initials} background={client.avatarBg} className="sales-client-avatar" />
        <span>
          <strong>{client.name}</strong>
          <small>{client.cid}</small>
        </span>
      </div>
      <div className="sales-client-contact">
        <span className={client.anon ? "is-muted" : ""}>{client.contactLine}</span>
        <small>{client.contactSub}</small>
      </div>
      <div className="sales-client-channels">
        {client.channels.map((channel) => (
          <span style={{ background: channel.bg, color: channel.color }} title={channel.full} key={channel.code}>
            <ChannelGlyph provider={channel.code} size={14} />
          </span>
        ))}
      </div>
      <div className="sales-client-last">
        <i style={{ background: client.lastDot }} />
        <span>
          <span>{client.lastWho}</span>
          <small>{client.lastWhen}</small>
        </span>
      </div>
      <div className="sales-client-open" style={{ color: client.openColor }}>{client.openDialogs}</div>
      <div className="sales-client-menu" onClick={(event) => event.stopPropagation()}>
        <Dropdown menu={{ items: menuItems }} open={menuOpen} onOpenChange={(open) => setMenu(open ? client.cid : null)} trigger={["click"]} overlayClassName="app-dropdown is-wide">
          <button className="row-menu-button" type="button" aria-label="Действия контакта"><Icon name="more" /></button>
        </Dropdown>
      </div>
    </div>
  );
}
