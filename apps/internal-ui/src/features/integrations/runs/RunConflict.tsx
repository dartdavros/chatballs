import { useState } from "react";
import { fmt, t } from "../../../i18n";
import { Button } from "../../../shared/ui-controls";
import { displayRunValue } from "./RunValues";
import type { RunConflict as Conflict } from "./types";
import "./conflict.css";

export function RunConflict({ conflict, disabled, apply }: {
  conflict: Conflict; disabled: boolean; apply: (choices: Record<string, string>) => void;
}) {
  const [choices, choose] = useState<Record<string, string>>({});
  const complete = conflict.items.every(item => choices[item.id]);
  return <section className="run-conflict">
    <div className="run-conflict-row is-head"><span>{t("runs.field")}</span><span>{conflict.leftTitle}</span><span>{conflict.rightTitle}</span></div>
    {conflict.items.map(item => <div className="run-conflict-row" key={item.id}>
      <strong>{item.field}</strong>
      {(["left", "right"] as const).map(side => <button type="button" key={side} className={`run-conflict-choice${choices[item.id] === side ? " is-selected" : ""}`}
        aria-pressed={choices[item.id] === side} disabled={disabled} onClick={() => choose({ ...choices, [item.id]: side })}>
        <span className="run-conflict-dot" aria-hidden="true" /><span><span>{displayRunValue(side === "left" ? item.leftSchema : item.rightSchema, item[side])}</span>
          <small>{item[`${side}At`] ? fmt.shortDateTime(item[`${side}At`]!) : "—"}</small></span>
      </button>)}
    </div>)}
    <footer><span>{t(complete ? "runs.conflict_selected" : "runs.conflict_choose")}</span>
      <Button variant="primary" disabled={disabled || !complete} onClick={() => apply(choices)}>{t("runs.conflict_apply")}</Button></footer>
  </section>;
}
