import { Icon } from "../../../shared/icons";
import { SearchInput } from "../../../shared/ui-controls";
import { channelOptions, productOptions, statusMap } from "./model";
import type { SalesClientsState } from "./useSalesClients";

export function SalesClientsFilters({ clients }: { clients: SalesClientsState }) {
  return (
    <div className="sales-clients-filterbar">
      <SearchInput className="sales-clients-search" value={clients.query} onChange={clients.setQuery} placeholder="Поиск по имени, email, телефону или логину…" />
      <SalesFilterDropdown
        active={clients.productFilter.length > 0 || clients.dropdown === "products"}
        count={clients.productFilter.length}
        icon="box"
        label={clients.productFilter.length ? "Продукты" : "Все продукты"}
        open={clients.dropdown === "products"}
        options={productOptions.map((option) => ({ ...option, checked: clients.productFilter.includes(option.code), dot: undefined }))}
        onOpenChange={(open) => clients.setDropdown(open ? "products" : null)}
        onToggleOption={(code) => clients.toggleProduct(code)}
      />
      <SalesFilterDropdown
        active={clients.channelFilter.length > 0 || clients.dropdown === "channels"}
        count={clients.channelFilter.length}
        icon="message"
        label={clients.channelFilter.length ? "Каналы" : "Все каналы"}
        open={clients.dropdown === "channels"}
        options={channelOptions.map((option) => ({ ...option, checked: clients.channelFilter.includes(option.code), dot: option.color }))}
        onOpenChange={(open) => clients.setDropdown(open ? "channels" : null)}
        onToggleOption={(code) => clients.toggleChannel(code)}
      />
      <button className={`sales-clients-chip ${clients.openOnly ? "active" : ""}`} type="button" onClick={clients.toggleOpenOnly}><span />С открытым диалогом</button>
      <button className={`sales-clients-chip ${clients.statusFilter === "lead" ? "active" : ""}`} type="button" onClick={() => clients.toggleStatus("lead")}><span style={{ background: statusMap.lead.color }} />Лиды</button>
      <button className={`sales-clients-chip ${clients.statusFilter === "client" ? "active" : ""}`} type="button" onClick={() => clients.toggleStatus("client")}><span style={{ background: statusMap.client.color }} />Клиенты</button>
      <div className="sales-clients-filter-spacer" />
      <button className="sales-clients-reset" type="button" onClick={clients.reset}>Сбросить</button>
    </div>
  );
}

function SalesFilterDropdown({ active, count, icon, label, open, options, onOpenChange, onToggleOption }: { active: boolean; count: number; icon: "box" | "message"; label: string; open: boolean; options: Array<{ code: string; name: string; checked: boolean; dot?: string }>; onOpenChange: (open: boolean) => void; onToggleOption: (code: string) => void }) {
  const items = options.map((option) => ({
    key: option.code,
    label: (
      <button
        type="button"
        onClick={(event) => {
          event.stopPropagation();
          onToggleOption(option.code);
        }}
      >
        <span className={`sales-clients-check ${option.checked ? "checked" : ""}`}>
          {option.checked && <Icon name="check" size={12} />}
        </span>
        {option.dot && <i className="sales-filter-dot" style={{ background: option.dot }} />}
        {option.name}
      </button>
    ),
  }));
  return (
    <div className="sales-clients-dd">
      <Dropdown menu={{ items }} open={open} onOpenChange={onOpenChange} trigger={["click"]} overlayClassName="app-dropdown is-wide">
        <button className={`sales-clients-dd-button ${active ? "active" : ""} ${open ? "open" : ""}`} type="button">
          <Icon name={icon} size={15} />
          {label}
          {count > 0 && <span>{count}</span>}
          <Icon name="chevron" size={13} />
        </button>
      </Dropdown>
    </div>
  );
}
import { Dropdown } from "antd";
