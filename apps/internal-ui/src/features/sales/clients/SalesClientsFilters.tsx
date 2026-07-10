import { Icon } from "../../../shared/icons";
import { SearchInput } from "../../../shared/ui-controls";
import { channelOptions, productOptions, statusMap } from "./model";
import type { SalesClientsState } from "./useSalesClients";

export function SalesClientsFilters({ clients }: { clients: SalesClientsState }) {
  return (
    <div className="sales-clients-filterbar">
      <SearchInput className="sales-clients-search" value={clients.query} onChange={clients.setQuery} placeholder="Поиск по имени, телефону или логину…" />
      {clients.dropdown !== null && <button className="sales-clients-dd-scrim" type="button" aria-label="Закрыть фильтр" onClick={clients.closeDropdown} />}
      <SalesFilterDropdown
        active={clients.productFilter.length > 0 || clients.dropdown === "products"}
        count={clients.productFilter.length}
        icon="box"
        label={clients.productFilter.length ? "Продукты" : "Все продукты"}
        open={clients.dropdown === "products"}
        options={productOptions.map((option) => ({ ...option, checked: clients.productFilter.includes(option.code), dot: undefined }))}
        onToggle={() => clients.toggleDropdown("products")}
        onToggleOption={(code) => clients.toggleProduct(code)}
      />
      <SalesFilterDropdown
        active={clients.channelFilter.length > 0 || clients.dropdown === "channels"}
        count={clients.channelFilter.length}
        icon="message"
        label={clients.channelFilter.length ? "Каналы" : "Все каналы"}
        open={clients.dropdown === "channels"}
        options={channelOptions.map((option) => ({ ...option, checked: clients.channelFilter.includes(option.code), dot: option.color }))}
        onToggle={() => clients.toggleDropdown("channels")}
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

function SalesFilterDropdown({ active, count, icon, label, open, options, onToggle, onToggleOption }: { active: boolean; count: number; icon: "box" | "message"; label: string; open: boolean; options: Array<{ code: string; name: string; checked: boolean; dot?: string }>; onToggle: () => void; onToggleOption: (code: string) => void }) {
  return (
    <div className="sales-clients-dd">
      <button className={`sales-clients-dd-button ${active ? "active" : ""} ${open ? "open" : ""}`} type="button" onClick={onToggle}>
        <Icon name={icon} size={15} />
        {label}
        {count > 0 && <span>{count}</span>}
        <Icon name="chevron" size={13} />
      </button>
      {open && (
        <div className="sales-clients-dd-menu">
          {options.map((option) => (
            <label className="sales-clients-dd-option" key={option.code}>
              <input type="checkbox" checked={option.checked} onChange={() => onToggleOption(option.code)} />
              <span className={`sales-clients-check ${option.checked ? "checked" : ""}`}>{option.checked && <Icon name="check" size={12} />}</span>
              {option.dot && <i style={{ background: option.dot }} />}
              {option.name}
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
