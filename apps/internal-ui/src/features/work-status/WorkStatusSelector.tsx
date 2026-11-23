import { Dropdown } from "antd";
import { useState } from "react";

import { Icon } from "../../shared/icons";
import { t } from "../../i18n";
import { statusChangedNote, statusDescription, statusLabel, workStatusCodes, type WorkStatusCode } from "./model";
import { WorkStatusIcon, WorkStatusLabel } from "./WorkStatusLabel";
import type { OwnWorkStatus } from "./useOwnWorkStatus";

// Выбор собственного статуса в блоке пользователя (кадр K2; сохранение — S2).
// Показывается сохранённый сервером статус: выбранный подставляется только на
// время запроса и с пометкой «сохраняем…».

export function WorkStatusSelector({ state, organization }: { state: OwnWorkStatus; organization: string }) {
  const [open, setOpen] = useState(false);
  const { saved, pending, choose } = state;
  const changed = statusChangedNote(saved?.changedAt ?? null);
  const items = [
    { key: "heading", type: "group" as const, label: t("work_status.menu_title", { organization }) },
    ...workStatusCodes.map((code) => ({
      key: code,
      disabled: !saved || Boolean(pending && pending.status !== code),
      label: <StatusOption code={code} state={state} onPick={() => choose(code)} />,
    })),
    {
      key: "footer",
      type: "group" as const,
      className: "work-status-footer",
      label: `${changed ? `${changed} ` : ""}${t("work_status.organization_only")}`,
    },
  ];
  return (
    <Dropdown
      trigger={["click"]}
      open={open}
      // Меню не закрывается выбором: в нём видно «сохраняем…» и результат.
      onOpenChange={(next, info) => { if (info.source !== "menu") setOpen(next); }}
      placement="topLeft"
      overlayClassName="app-dropdown has-wrapped-options work-status-menu"
      menu={{ items }}
    >
      <button type="button" className="row-menu-button work-status-trigger" title={t("work_status.title")} aria-busy={Boolean(pending)}>
        {pending ? (
          <span className="work-status is-saving">
            <WorkStatusIcon code={pending.status} />
            <span>{statusLabel(pending.status, true)} · {t("work_status.saving")}</span>
          </span>
        ) : <WorkStatusLabel value={saved} time />}
        <Icon name="chevron" size={11} />
      </button>
    </Dropdown>
  );
}

function StatusOption({ code, state, onPick }: { code: WorkStatusCode; state: OwnWorkStatus; onPick: () => void }) {
  const { saved, pending } = state;
  const isSaved = saved?.status === code;
  const isPending = pending?.status === code;
  return (
    <button type="button" className={(pending ? isPending : isSaved) ? "is-checked" : ""} onClick={onPick}>
      <WorkStatusIcon code={code} size={15} />
      <span className="work-status-option-text">
        <span>{statusLabel(code)}</span>
        {!pending && <small>{statusDescription(code)}</small>}
      </span>
      {isPending && <small>{t("work_status.saving")}</small>}
      {pending && isSaved && <small>{t("work_status.current")}</small>}
      {!pending && isSaved && <Icon name="check" size={15} />}
    </button>
  );
}

/** Ошибка под блоком пользователя (кадр S4): остался прежний статус, можно повторить. */
export function WorkStatusSaveError({ state }: { state: OwnWorkStatus }) {
  const { failed, saved, retry } = state;
  if (!failed || !saved) return null;
  return (
    <div className="work-status-notice is-error" role="alert">
      <span>
        {t("work_status.failed", { requested: statusLabel(failed.status), saved: statusLabel(saved.status, true) })}{" "}
        <button type="button" className="link is-strong" onClick={retry}>{t("work_status.retry")}</button>
      </span>
    </div>
  );
}
