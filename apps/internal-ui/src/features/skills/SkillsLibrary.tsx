import { useState } from "react";
import { t } from "../../i18n";
import { EmptyState, ErrorScreen, PermissionScreen } from "../../shared/ui";
import { Button, FilterDropdown, SearchInput } from "../../shared/ui-controls";
import type { AgentRef } from "../agents/model";
import { SkillsTable } from "./SkillsTable";
import { SkillGlyph } from "./SkillGlyph";
import { useSkillsList } from "./useSkillsList";
export function SkillsLibrary({
  agents,
  open,
  remove,
  openAgent,
  back,
}: {
  agents: AgentRef[];
  open: (id: string) => void;
  remove: (id: string) => void;
  openAgent: (id: number) => void;
  back: () => void;
}) {
  const [query, setQuery] = useState("");
  const [agent, setAgent] = useState("");
  const [agentOpen, setAgentOpen] = useState(false);
  const list = useSkillsList(query, agent);
  const create = (
    <Button variant="primary" className="agents-create" icon="plus" onClick={() => open("new")}>
      {t("skills.create")}
    </Button>
  );
  if (list.forbidden) return <PermissionScreen onReturn={back} />;
  return (
    <div className="agents-page skills-library">
      <header className="agents-header">
        <div>
          <h2>{t("skills.title")}</h2>
          <p>{t("skills.lead")}</p>
        </div>
        {create}
      </header>
      <div className="skills-filters">
        <SearchInput
          clearable
          placeholder={t("skills.search")}
          value={query}
          onChange={(value) => setQuery(value.slice(0, 200))}
        />
        <FilterDropdown
          caption={t("common.agent")}
          label={agents.find(item => String(item.id) === agent)?.name ?? t("common.all")}
          open={agentOpen}
          onOpenChange={setAgentOpen}
          selected={agent ? [agent] : []}
          onSelect={(value) => { setAgent(value); setAgentOpen(false); }}
          options={[{ value: "", label: t("common.all") }, ...agents.map(item => ({ value: String(item.id), label: item.name }))]}
        />
      </div>
      {list.errorText ? (
        <ErrorScreen retry={() => void list.reload()} />
      ) : !list.loading && list.total === 0 ? (
        query || agent ? (
          <EmptyState title={t("skills.no_results")} />
        ) : (
          <div className="skills-empty">
            <span className="skill-tile">
              <SkillGlyph size={26} />
            </span>
            <h3>{t("skills.empty")}</h3>
            <p>{t("skills.empty_help")}</p>
            {create}
          </div>
        )
      ) : (
        <SkillsTable list={list} open={open} remove={remove} openAgent={openAgent} />
      )}
    </div>
  );
}
