import { useEffect, useRef, useState } from "react";
import { t } from "../../i18n";
import { TokenEditor, type TokenEditorHandle } from "../reply-templates/TokenEditor";
import { TemplateVariableMenu } from "../reply-templates/TemplateVariableMenu";
import type { AgentCard, AgentPatch } from "./model";

export function AgentGreetingCard({ card, canManage, busy, apply }: {
  card: AgentCard;
  canManage: boolean;
  busy: boolean;
  apply: (patch: AgentPatch) => Promise<boolean>;
}) {
  const saved = card.greeting ?? "";
  const variables = card.greetingVariables ?? [];
  const [draft, setDraft] = useState(saved);
  const editor = useRef<TokenEditorHandle>(null);
  useEffect(() => setDraft(saved), [saved]);
  return (
    <section className="agent-card">
      <div className="agent-card-head">
        <h3>{t("ai.agent_greeting")}</h3>
        <small>{t("ai.agent_greeting_hint")}</small>
      </div>
      <div className="agent-field is-text">
        {canManage ? <><TemplateVariableMenu variant="secondary" variables={busy ? [] : variables} onPick={({ token }) => editor.current?.insert(token)} />
          <TokenEditor label={t("ai.agent_greeting")} value={draft} onChange={setDraft}
            variables={variables} editorRef={editor} disabled={busy} className="template-form-editor" />
        </> : <span className="agent-field-static">{saved || "—"}</span>}
      </div>
      {canManage && draft !== saved && <div className="agent-dirty">
        <small>{t("ai.there_unsaved_changes_they_take")}</small>
        <button type="button" disabled={busy} onClick={() => setDraft(saved)}>{t("ai.undo")}</button>
        <button className="is-primary" type="button" disabled={busy} onClick={() => void apply({ greeting: draft })}>{t("common.save")}</button>
      </div>}
    </section>
  );
}
