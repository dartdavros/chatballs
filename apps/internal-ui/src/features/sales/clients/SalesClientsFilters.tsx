import { FilterDropdown, SearchInput } from "../../../shared/ui-controls";
import { channelOptions, type ClientAgentRef } from "./model";
import type { SalesClientsState } from "./useSalesClients";

// Фильтры списка (кадры K1/K2): поиск, «Все каналы», «Все агенты», чип
// «С открытым диалогом»; «Сбросить» появляется только когда фильтр применён.

// Агенты для фильтра приходят из справочника агентов: список контактов теперь
// постраничный, и собрать их по загруженной странице нельзя.
export function SalesClientsFilters({ clients, agents }: { clients: SalesClientsState; agents: ClientAgentRef[] }) {
  return (
    <div className="sales-clients-filterbar">
      <SearchInput
        className="sales-clients-search"
        value={clients.query}
        onChange={clients.setQuery}
        hotkey="/"
        placeholder="Имя, email, телефон или логин…"
      />
      <FilterDropdown
        icon="message"
        label={clients.channelFilter.length ? "Каналы" : "Все каналы"}
        multiple
        open={clients.dropdown === "channels"}
        options={channelOptions.map((option) => ({ value: String(option.code), label: option.name, dot: option.color }))}
        selected={clients.channelFilter.map(String)}
        onOpenChange={(open) => clients.setDropdown(open ? "channels" : null)}
        onSelect={(value) => clients.toggleChannel(value)}
      />
      <FilterDropdown
        icon="robot"
        label={clients.agentFilter.length ? "Агенты" : "Все агенты"}
        multiple
        open={clients.dropdown === "agents"}
        options={agents.map((agent) => ({ value: String(agent.id), label: agent.name }))}
        selected={clients.agentFilter.map(String)}
        onOpenChange={(open) => clients.setDropdown(open ? "agents" : null)}
        onSelect={(value) => clients.toggleAgent(Number(value))}
      />
      <button className={`sales-clients-chip ${clients.openOnly ? "active" : ""}`} type="button" onClick={clients.toggleOpenOnly}>
        <i />С открытым диалогом
      </button>
      <div className="sales-clients-filter-spacer" />
      {clients.filtered && <button className="sales-clients-reset" type="button" onClick={clients.reset}>Сбросить</button>}
    </div>
  );
}
