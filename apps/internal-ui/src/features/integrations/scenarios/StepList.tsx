import { Dropdown } from "antd";
import { useState } from "react";
import { t } from "../../../i18n";
import { Icon } from "../../../shared/icons";
import { Button } from "../../../shared/ui-controls";
import { blockTitle, childLists, copyBlock } from "./model";
import type { Block, BlockLocation, EditorCatalog, ScenarioDocument } from "./types";
import { stepIcon, stepSummary } from "./stepPresentation";

type Props = { steps: Block[]; catalog: EditorCatalog; document: ScenarioDocument; onChange: (steps: Block[]) => void;
  onOpen: (id: string) => void; onAdd: (location: BlockLocation) => void; parent?: string | null; branch?: string; prefix?: string };

export function StepList({ steps, catalog, document, onChange, onOpen, onAdd, parent = null, branch = "", prefix = "" }: Props) {
  const [dragged, setDragged] = useState<string | null>(null);
  function move(index: number, destination: number) {
    const next = structuredClone(steps); const [step] = next.splice(index, 1); next.splice(destination, 0, step); onChange(next);
  }
  function changeChild(blockIndex: number, key: string, list: Block[]) {
    const next = structuredClone(steps); const block = next[blockIndex];
    if (key.startsWith("branches.")) block.branches![Number(key.split(".")[1])] = list;
    else if (key === "then" || key === "else" || key === "body" || key === "catch") block[key] = list;
    onChange(next);
  }
  return <div className="scenario-steps-list">
    {steps.map((step, index) => {
      const number = `${prefix}${index + 1}`;
      const menu = [
        { key: "up", label: t("scenarios.up"), disabled: index === 0, onClick: () => move(index, index - 1) },
        { key: "down", label: t("scenarios.down"), disabled: index === steps.length - 1, onClick: () => move(index, index + 1) },
        { key: "copy", label: t("scenarios.copy"), onClick: () => { const next = [...steps]; next.splice(index + 1, 0, copyBlock(step)); onChange(next); } },
        { key: "delete", label: t("scenarios.remove"), danger: true, onClick: () => onChange(steps.filter(s => s.id !== step.id)) },
      ];
      return <div key={step.id} className="scenario-step-group">
        <div className={`scenario-step${dragged === step.id ? " is-dragging" : ""}`} onDragOver={event => { if (dragged) event.preventDefault(); }}
          onDrop={event => { event.preventDefault(); const from = steps.findIndex(s => s.id === dragged); if (from >= 0) move(from, index); setDragged(null); }}>
          <button type="button" className="scenario-step-number" draggable aria-label={t("scenarios.step_number", { number })}
            onDragStart={() => setDragged(step.id)} onDragEnd={() => setDragged(null)}
            onKeyDown={event => { if (event.key === "Escape") setDragged(null); if (event.key === "ArrowUp" && index > 0) { event.preventDefault(); move(index, index - 1); }
              if (event.key === "ArrowDown" && index < steps.length - 1) { event.preventDefault(); move(index, index + 1); } }}>{number}</button>
          <button type="button" className="scenario-step-main" onClick={() => onOpen(step.id)}>
            <span className="scenario-step-icon"><Icon name={stepIcon(step)} size={16} /></span>
            <span><strong>{blockTitle(step, catalog)}</strong><small>{stepSummary(step, document, catalog)}</small></span>
          </button>
          <Dropdown overlayClassName="app-dropdown" trigger={["click"]} menu={{ items: menu }}>
            <button type="button" className="row-menu-button" aria-label={t("scenarios.step_menu")}><Icon name="more" size={16} /></button>
          </Dropdown>
        </div>
        {childLists(step).map(([key, list], i) => <div className="scenario-branch" key={key}>
          <strong>{key.startsWith("branches.") ? t("scenarios.branch", { number: i + 1 }) : t(`scenarios.${key as "then" | "else" | "body" | "catch"}`)}</strong>
          <StepList steps={list} catalog={catalog} document={document} parent={step.id} branch={key} prefix={`${number}.`} onChange={next => changeChild(index, key, next)} onOpen={onOpen} onAdd={onAdd} />
        </div>)}
        {step.kind === "parallel" && <button type="button" className="link is-muted" onClick={() => {
          const next = structuredClone(steps); next[index].branches!.push([]); onChange(next);
        }}>{t("scenarios.add_branch")}</button>}
      </div>;
    })}
    {!steps.length && !parent ? <div className="scenario-first-step"><strong>{t("scenarios.first_step")}</strong><span>{t("scenarios.first_step_lead")}</span>
      <Button variant="primary" onClick={() => onAdd({ parent, branch })}>{t("scenarios.add_step")}</Button></div>
      : <button type="button" className={`link has-icon ${parent ? "is-muted" : ""}`} onClick={() => onAdd({ parent, branch })}><Icon name="plus" size={14} />{t("scenarios.add_step")}</button>}
  </div>;
}
