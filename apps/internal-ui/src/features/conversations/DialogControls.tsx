import { useEffect, useState } from "react";

import { ContextSection } from "./ContextSection";
import { PriorityBars } from "./DialogList";
import {
  createConversationLabel,
  fetchConversationLabels,
  setConversationArchived,
  setConversationAssignee,
  setConversationGroup,
  setConversationLabels,
  setConversationNote,
  setConversationPriority,
  type ApiConversation,
  type ConversationLabelRef,
  type ConversationPriority,
} from "./model";
import type { EmployeeGroupRef } from "../../types";

// Блок «Диалог» контекст-панели (дизайн-базлайн v2 §5): ответственный, группа,
// приоритет, метки, заметка. Селекты группы/ответственного заполняются данными
// менеджера; у сотрудника значения read-only, взятие диалога — в шапке ленты.

const PRIORITY_OPTIONS: Array<[ConversationPriority, string]> = [
  ["NONE", "Не задан"],
  ["LOW", "Низкий"],
  ["MEDIUM", "Средний"],
  ["HIGH", "Высокий"],
];

export function DialogControls({
  detail,
  groups,
  employees,
  applyConversation,
}: {
  detail: ApiConversation;
  groups: EmployeeGroupRef[];
  employees: Array<{ id: number; name: string }>;
  applyConversation: (updated: ApiConversation) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [errorText, setErrorText] = useState("");
  const onError = (text: string) => setErrorText(text);
  const [note, setNote] = useState(detail.note);
  const [labels, setLabels] = useState<ConversationLabelRef[]>([]);
  const [newLabel, setNewLabel] = useState("");

  useEffect(() => {
    setNote(detail.note);
    setNewLabel("");
  }, [detail.id, detail.note]);

  useEffect(() => {
    fetchConversationLabels().then(setLabels).catch(() => setLabels([]));
  }, []);

  async function run(action: () => Promise<ApiConversation>) {
    setBusy(true);
    setErrorText("");
    try {
      applyConversation(await action());
    } catch (error) {
      onError(error instanceof Error ? error.message : "Не удалось сохранить");
    } finally {
      setBusy(false);
    }
  }

  async function addLabel() {
    const name = newLabel.trim();
    if (!name) return;
    setBusy(true);
    try {
      const label = await createConversationLabel(name);
      setLabels((current) =>
        current.some((item) => item.id === label.id) ? current : [...current, label],
      );
      const ids = [...detail.labels.map((item) => item.id), label.id];
      applyConversation(await setConversationLabels(detail.id, [...new Set(ids)]));
      setNewLabel("");
    } catch (error) {
      onError(error instanceof Error ? error.message : "Не удалось добавить метку");
    } finally {
      setBusy(false);
    }
  }

  const assignedIds = new Set(detail.labels.map((item) => item.id));
  const availableLabels = labels.filter((item) => !assignedIds.has(item.id));
  const noteDirty = note !== detail.note;

  return (
    <ContextSection title="ДИАЛОГ">
      <div className="dialog-controls">
        {errorText && <p className="dialog-controls-error">{errorText}</p>}
        <label className="dialog-controls-field">
          <span>Ответственный</span>
          {employees.length > 0 ? (
            <select
              disabled={busy}
              value={detail.assignedOperatorId ?? ""}
              onChange={(event) =>
                void run(() =>
                  setConversationAssignee(
                    detail.id,
                    event.target.value ? Number(event.target.value) : null,
                  ),
                )
              }
            >
              <option value="">Не назначен</option>
              {employees.map((employee) => (
                <option value={employee.id} key={employee.id}>{employee.name}</option>
              ))}
            </select>
          ) : (
            <b>{detail.assignedOperator?.name ?? "Не назначен"}</b>
          )}
        </label>

        <label className="dialog-controls-field">
          <span>Группа</span>
          {groups.length > 0 ? (
            <select
              disabled={busy}
              value={detail.group?.id ?? ""}
              onChange={(event) =>
                void run(() =>
                  setConversationGroup(
                    detail.id,
                    event.target.value ? Number(event.target.value) : null,
                  ),
                )
              }
            >
              <option value="">Без группы — видят все</option>
              {groups.map((group) => (
                <option value={group.id} key={group.id}>{group.name}</option>
              ))}
            </select>
          ) : (
            <b>{detail.group?.name ?? "Без группы"}</b>
          )}
        </label>

        <label className="dialog-controls-field">
          <span>Приоритет</span>
          <span className="dialog-controls-priority">
            <PriorityBars priority={detail.priority} />
            <select
              disabled={busy}
              value={detail.priority}
              onChange={(event) =>
                void run(() =>
                  setConversationPriority(
                    detail.id,
                    event.target.value as ConversationPriority,
                  ),
                )
              }
            >
              {PRIORITY_OPTIONS.map(([value, label]) => (
                <option value={value} key={value}>{label}</option>
              ))}
            </select>
          </span>
        </label>

        <div className="dialog-controls-field">
          <span>Метки</span>
          <div className="dialog-controls-labels">
            {detail.labels.map((label) => (
              <b className="sales-dialog-label" key={label.id}>
                <i style={{ background: label.color || "var(--n-5)" }} />
                {label.name}
                <button
                  aria-label={`Снять метку ${label.name}`}
                  disabled={busy}
                  type="button"
                  onClick={() =>
                    void run(() =>
                      setConversationLabels(
                        detail.id,
                        detail.labels
                          .filter((item) => item.id !== label.id)
                          .map((item) => item.id),
                      ),
                    )
                  }
                >
                  ×
                </button>
              </b>
            ))}
            {availableLabels.length > 0 && (
              <select
                className="dialog-controls-add-label"
                disabled={busy}
                value=""
                onChange={(event) => {
                  const id = Number(event.target.value);
                  if (!id) return;
                  void run(() =>
                    setConversationLabels(detail.id, [
                      ...detail.labels.map((item) => item.id),
                      id,
                    ]),
                  );
                }}
              >
                <option value="">+ Метка</option>
                {availableLabels.map((label) => (
                  <option value={label.id} key={label.id}>{label.name}</option>
                ))}
              </select>
            )}
          </div>
          <div className="dialog-controls-new-label">
            <input
              disabled={busy}
              placeholder="Новая метка"
              value={newLabel}
              onChange={(event) => setNewLabel(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  void addLabel();
                }
              }}
            />
            <button disabled={busy || !newLabel.trim()} type="button" onClick={() => void addLabel()}>
              Добавить
            </button>
          </div>
        </div>

        <div className="dialog-controls-field">
          <span>Заметка</span>
          <textarea
            disabled={busy}
            placeholder="Внутренняя заметка — клиент её не видит"
            rows={3}
            value={note}
            onChange={(event) => setNote(event.target.value)}
          />
          {noteDirty && (
            <div className="dialog-controls-note-actions">
              <button disabled={busy} type="button" onClick={() => setNote(detail.note)}>Отменить</button>
              <button
                className="primary"
                disabled={busy}
                type="button"
                onClick={() => void run(() => setConversationNote(detail.id, note))}
              >
                Сохранить
              </button>
            </div>
          )}
        </div>
      </div>
    </ContextSection>
  );
}

export function archiveConversationAction(
  detail: ApiConversation,
  applyConversation: (updated: ApiConversation) => void,
  onError: (text: string) => void,
): Promise<boolean> {
  return setConversationArchived(detail.id, true)
    .then((updated) => {
      applyConversation(updated);
      return true;
    })
    .catch((error) => {
      onError(error instanceof Error ? error.message : "Не удалось удалить диалог");
      return false;
    });
}
