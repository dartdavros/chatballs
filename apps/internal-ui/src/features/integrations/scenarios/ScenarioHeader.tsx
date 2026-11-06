import { Dropdown } from "antd";
import { t } from "../../../i18n";
import { Icon } from "../../../shared/icons";
import { StatusPill } from "../../../shared/ui";
import { Button } from "../../../shared/ui-controls";
import type { ScenarioEditorState } from "./useScenarioEditor";

export function ScenarioHeader({ editor, onDelete }: { editor: ScenarioEditorState; onDelete: () => void }) {
  const { draft, saving } = editor;
  if (!draft) return null;
  const menu = [
    ...(draft.enabled ? [{ key: "disable", label: <button type="button">{t("scenarios.disable")}</button>, onClick: () => void editor.save(false) }] : []),
    { key: "copy", label: <button type="button" disabled={!draft.id || saving || editor.dirty}>{t("scenarios.copy")}</button>,
      disabled: !draft.id || saving || editor.dirty, onClick: () => void editor.copy() },
    { key: "delete", label: <button type="button" className="danger" disabled={!draft.id || saving}>{t("scenarios.delete")}</button>,
      danger: true, disabled: !draft.id || saving, onClick: onDelete },
  ];
  return <>
    {draft.automationError && <p className="scenario-banner" role="alert">{draft.automationError}</p>}
    <button className="link is-muted has-icon scenario-back" type="button" disabled={saving} onClick={() => editor.open(null)}>
      <Icon name="chevronLeft" size={14} />{t("scenarios.title")}</button>
    <header className="scenario-head">
      <div className="scenario-heading"><input aria-label={t("scenarios.name")} className="scenario-name" value={draft.name}
        disabled={saving} onChange={event => editor.setDraft({ ...draft, name: event.target.value })} />
        <div className="scenario-origin"><StatusPill status={draft.enabled ? "healthy" : "draft"} label={t(draft.enabled ? "scenarios.on" : "scenarios.off")} />
          <span>{t(draft.origin.key ? "scenarios.origin_preset" : "scenarios.origin_custom")}</span></div>
      </div>
      <div className="scenario-head-actions">
        {editor.dirty && <><span>{t("scenarios.unsaved")}</span><Button variant="secondary" disabled={saving || editor.conflict}
          onClick={() => void editor.save()}>{t("scenarios.save")}</Button></>}
        {!draft.enabled && <Button variant="primary" disabled={saving || editor.conflict} onClick={() => void editor.save(true)}>{t("scenarios.enable")}</Button>}
        <Dropdown overlayClassName="app-dropdown" placement="bottomRight" trigger={["click"]} menu={{ items: menu }}>
          <button type="button" className="row-menu-button" aria-label={t("scenarios.more")} disabled={saving}><Icon name="more" size={16} /></button>
        </Dropdown>
      </div>
    </header>
  </>;
}
