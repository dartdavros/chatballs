import { Modal } from "antd";
import { useState } from "react";
import { t, tn } from "../../i18n";
import { BackLink, Button } from "../../shared/ui-controls";
import { EmptyState, ErrorScreen, LoadingState, PermissionScreen } from "../../shared/ui";
import { SkillFields } from "./SkillFields";
import { SkillSidebar } from "./SkillSidebar";
import { SkillTemplates } from "./SkillTemplates";
import { TemplateEditor } from "./template-editor/TemplateEditor";
import { newTemplate } from "./template-editor/model";
import { useSkillDraft } from "./useSkillDraft";
import { useSkillLeaveGuard } from "./useSkillLeaveGuard";
import { SkillLeaveDialog } from "./SkillLeaveDialog";
import { SkillEditorHeader } from "./SkillEditorHeader";
import { SkillSaveError } from "./SkillSaveError";

export function SkillEditor({
  id,
  back,
  openAgent,
  remove,
}: {
  id: string;
  back: () => void;
  openAgent: (id: number) => void;
  remove: (id: string) => void;
}) {
  const state = useSkillDraft(id);
  const {
    saved,
    draft,
    setDraft,
    dirty,
    loading,
    failure,
    busy,
    error,
    conflict,
    basis,
    attempted,
    save,
    load,
    changeBasis,
    reset,
  } = state;
  const leave = useSkillLeaveGuard(dirty);
  const [template, setTemplate] = useState<string | null>(null);
  const [replacing, setReplacing] = useState<(() => void) | null>(null);
  const confirmReplace = (action: () => void) => setReplacing(() => action);
  const saveLabel = !saved
    ? t("skills.create")
    : saved.agentCount
      ? tn("skills.save_for", saved.agentCount)
      : t("common.save");
  if (failure === "forbidden") return <PermissionScreen onReturn={back} />;
  if (failure === "missing")
    return (
      <div className="agents-page">
        <BackLink label={t("skills.title")} onClick={back} />
        <EmptyState title={t("skills.not_found")} />
      </div>
    );
  if (failure === "load") return <ErrorScreen retry={() => void load()} />;
  if (loading) return <LoadingState />;

  const footer = (
    <div className="skill-actions">
      <Button variant="secondary" disabled={busy} onClick={() => leave.request(back)}>
        {t("common.cancel")}
      </Button>
      <Button variant="primary" disabled={busy || conflict || (!dirty && !!saved)} onClick={() => void save()}>
        {saveLabel}
      </Button>
    </div>
  );
  return (
    <>
      {template ? (
        <TemplateEditor key={template} state={state} templateId={template}
          library={() => leave.request(back)}
          back={() => leave.request(() => setTemplate(null))}
          parentErrors={() => { leave.stay(); setTemplate(null); }}
          refresh={() => confirmReplace(() => void load())} />
      ) : (
        <div className="skill-editor">
          <BackLink label={t("skills.title")} onClick={() => leave.request(back)} />
          <SkillEditorHeader skill={saved} busy={busy} remove={() => saved && remove(saved.id)} actions={footer} />
          <SkillSaveError state={state} refresh={() => confirmReplace(() => void load())} openTemplate={setTemplate} />
          <div className="skill-editor-grid">
            <div className="skill-column">
              <SkillFields
                draft={draft}
                change={setDraft}
                attempted={attempted}
                busy={busy}
                creating={!saved}
                basis={basis}
                serverErrors={state.validationErrors}
                changeBasis={(next) => {
                  if (dirty) confirmReplace(() => void changeBasis(next));
                  else void changeBasis(next);
                }}
              />
              <SkillTemplates
                templates={draft.templates}
                open={(templateId) => {
                  if (templateId) setTemplate(templateId);
                  else {
                    const next = newTemplate();
                    setDraft({ ...draft, templates: [...draft.templates, next] });
                    setTemplate(next.id);
                  }
                }}
                remove={(templateId) =>
                  setDraft({ ...draft, templates: draft.templates.filter((item) => item.id !== templateId) })
                }
              />
            </div>
            <SkillSidebar skill={saved} openAgent={(agentId) => leave.request(() => openAgent(agentId))} />
          </div>
          {dirty && (
            <footer className="skill-save-footer">
              <small role="status">{t("skills.unsaved")}</small>
              <Button variant="secondary" disabled={busy} onClick={() => confirmReplace(reset)}>
                {t("skills.reset")}
              </Button>
              <Button variant="primary" disabled={busy || conflict} onClick={() => void save()}>
                {saveLabel}
              </Button>
            </footer>
          )}
        </div>
      )}
      <Modal
        open={!!replacing}
        title={t("skills.replace")}
        onCancel={() => setReplacing(null)}
        okText={t("skills.replace_action")}
        cancelText={t("common.cancel")}
        onOk={() => {
          replacing?.();
          setReplacing(null);
        }}
      />
      <SkillLeaveDialog leave={leave} busy={busy} conflict={conflict} save={async () => {
        const result = await save();
        if (!result && state.parentInvalid()) { setTemplate(null); leave.stay(); }
        return result;
      }} draft={draft} error={error} template={!!template} templateName={draft.templates.find((item) => item.id === template)?.name} />
    </>
  );
}
