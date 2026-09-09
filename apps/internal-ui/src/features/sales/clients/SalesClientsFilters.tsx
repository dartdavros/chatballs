import { FilterDropdown, SearchInput } from "../../../shared/ui-controls";
import { channelOptions } from "./model";

/** Агент в фильтре: только то, что рисует выпадающий список. */
export type AgentFilterOption = { id: number; name: string };
import type { SalesClientsState } from "./useSalesClients";
import { t } from "../../../i18n";

// Фильтры списка (кадры K1/K2): поиск, «Все каналы», «Все агенты», чип
// «С открытым диалогом»; «Сбросить» появляется только когда фильтр применён.

// Агенты для фильтра приходят из справочника агентов: список контактов теперь
// постраничный, и собрать их по загруженной странице нельзя.
export function SalesClientsFilters({ clients, agents }: { clients: SalesClientsState; agents: AgentFilterOption[] }) {
  return (
    <div className="sales-clients-filterbar">
      <SearchInput
        className="sales-clients-search"
        value={clients.query}
        onChange={clients.setQuery}
        hotkey="/"
        placeholder={t("sales.name_email_phone_or_username")}
      />
      <FilterDropdown
        icon="message"
        label={clients.channelFilter.length ? t("common.channels") : t("sales.all_channels")}
        multiple
        open={clients.dropdown === "channels"}
        options={channelOptions.map((option) => ({ value: String(option.code), label: option.name, dot: option.color }))}
        selected={clients.channelFilter.map(String)}
        onOpenChange={(open) => clients.setDropdown(open ? "channels" : null)}
        onSelect={(value) => clients.toggleChannel(value)}
      />
      <FilterDropdown
        icon="robot"
        label={clients.agentFilter.length ? t("common.agents") : t("sales.all_agents")}
        multiple
        open={clients.dropdown === "agents"}
        options={agents.map((agent) => ({ value: String(agent.id), label: agent.name }))}
        selected={clients.agentFilter.map(String)}
        onOpenChange={(open) => clients.setDropdown(open ? "agents" : null)}
        onSelect={(value) => clients.toggleAgent(Number(value))}
      />
      <button className={`sales-clients-chip ${clients.openOnly ? "active" : ""}`} type="button" onClick={clients.toggleOpenOnly}>
        <i />{t("sales.with_open_conversation")}</button>
      <div className="sales-clients-filter-spacer" />
      {clients.filtered && <button className="sales-clients-reset" type="button" onClick={clients.reset}>{t("common.reset")}</button>}
    </div>
  );
}
