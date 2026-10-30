import { useState } from "react";
import { t } from "../../../i18n";
import { FieldDialog } from "../../skills/template-editor/FieldDialog";
import type { ServiceField } from "../services/types";
import { fieldFromNode } from "./valueFields";

/** Reuses the existing object/list schema dialog; no JSON editor. */
export function AddObjectField({ names, onAdd }: { names: string[]; onAdd: (field: ServiceField) => void }) {
  const [open, setOpen] = useState(false);
  return <>
    <button type="button" className="link" onClick={() => setOpen(true)}>{t("scenarios.add_field")}</button>
    {open && <FieldDialog close={() => setOpen(false)} schema={{ type: "object", properties: Object.fromEntries(names.map(name => [name, { type: "string" as const }])) }}
      change={schema => { const entry = Object.entries(schema.properties ?? {}).find(([name]) => !names.includes(name)); if (entry) onAdd(fieldFromNode(entry[0], entry[1])); }} />}
  </>;
}
