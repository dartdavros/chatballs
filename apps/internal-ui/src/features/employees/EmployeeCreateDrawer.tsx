import { useState, type ReactNode } from "react";

import { Icon } from "../../shared/icons";
import { groupColorOf } from "../conversations/model";
import type { EmployeeGroup, Role } from "../../types";
import { createEmployee, type IssuedPassword, type PasswordMode } from "./api";
import { t } from "../../i18n";

// Новый сотрудник (дизайн-базлайн v2, кадры E5/E6): выезжающая панель 520px,
// четыре шага — учётные данные · роль · должность и группы · пароль.

const ROLE_OPTIONS: Array<{ value: Extract<Role, "ADMIN" | "EMPLOYEE">; label: string; description: string }> = [
  { value: "EMPLOYEE", label: t("common.operator"), description: t("admin.works_chat_sees_conversations_their") },
  { value: "ADMIN", label: t("common.administrator"), description: t("admin.full_access_identical_owner_owner") },
];

const PASSWORD_OPTIONS: Array<{ value: PasswordMode; label: string; description: string }> = [
  { value: "mail", label: t("admin.send_work_email"), description: t("admin.operator_gets_email_with_first") },
  { value: "show", label: t("admin.generate_show_me"), description: t("admin.password_shown_once_after_creation") },
];

export function EmployeeCreateDrawer({ groups, onClose, onCreated }: {
  groups: EmployeeGroup[];
  onClose: () => void;
  onCreated: (password: IssuedPassword | null) => void;
}) {
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Extract<Role, "ADMIN" | "EMPLOYEE">>("EMPLOYEE");
  const [positionTitle, setPositionTitle] = useState("");
  const [groupIds, setGroupIds] = useState<number[]>([]);
  const [passwordMode, setPasswordMode] = useState<PasswordMode>("mail");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const canSubmit = Boolean(fullName.trim() && email.trim() && positionTitle.trim() && !submitting);

  function toggleGroup(groupId: number) {
    setGroupIds((items) => items.includes(groupId) ? items.filter((item) => item !== groupId) : [...items, groupId]);
  }

  async function submit() {
    if (!canSubmit) return;
    setSubmitting(true);
    setError("");
    try {
      const issued = await createEmployee({ fullName, phone, email, role, positionTitle, groupIds, passwordMode });
      onCreated(issued);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("admin.creation_failed"));
      setSubmitting(false);
    }
  }

  const footerHint = passwordMode === "mail"
    ? t("admin.first_password_goes_to", { email: email.trim() || t("admin.work_email") })
    : t("admin.password_appears_right_after_creation");

  return (
    <>
      <button className="employee-drawer-scrim" type="button" aria-label={t("admin.close_form")} onClick={onClose} />
      <aside className="employee-create-drawer" aria-label={t("admin.new_operator")}>
        <header>
          <div>
            <strong>{t("admin.new_operator")}</strong>
            <span>{t("admin.credentials_role_groups")}</span>
          </div>
          <button type="button" aria-label={t("common.close")} onClick={onClose}><Icon name="xCircle" size={19} strokeWidth={1.8} /></button>
        </header>

        <div className="employee-create-body">
          <CreateStep number="1" title={t("admin.credentials")}>
            <div className="employee-create-grid">
              <CreateField label={t("common.name")} value={fullName} onChange={setFullName} placeholder={t("admin.first_last_name")} />
              <CreateField label={t("common.phone")} value={phone} onChange={setPhone} placeholder="+7 …" />
              <CreateField className="wide" label={t("admin.work_email_used_sign")} value={email} onChange={setEmail} placeholder="name@company.ru" mono />
            </div>
          </CreateStep>

          <CreateStep number="2" title={t("common.role")}>
            <div className="employee-choice-list">
              {ROLE_OPTIONS.map((option) => (
                <ChoiceOption
                  active={role === option.value}
                  description={option.description}
                  label={option.label}
                  onClick={() => setRole(option.value)}
                  key={option.value}
                />
              ))}
            </div>
          </CreateStep>

          <CreateStep number="3" title={t("admin.position_groups")}>
            <CreateField className="is-single" label={t("common.position")} value={positionTitle} onChange={setPositionTitle} placeholder={t("admin.e_g_operator")} />
            {groups.length > 0 ? (
              <>
                <div className="employee-group-picks">
                  {groups.map((group) => {
                    const active = groupIds.includes(group.id);
                    return (
                      <button className={`employee-group-pick ${active ? "is-on" : ""}`} type="button" aria-pressed={active} onClick={() => toggleGroup(group.id)} key={group.id}>
                        <i>{active && <Icon name="check" size={11} strokeWidth={3} />}</i>
                        <span>
                          <strong><i className="employee-group-dot" style={{ background: groupColorOf(group.id, group.color) }} />{group.name}</strong>
                          <small>{t("admin.member_count", { count: group.memberCount })}</small>
                        </span>
                      </button>
                    );
                  })}
                </div>
                <p className="employee-create-note">{t("admin.with_no_groups_operator_sees")}</p>
              </>
            ) : (
              <p className="employee-create-note">{t("admin.there_no_groups_yet_so")}</p>
            )}
          </CreateStep>

          <CreateStep number="4" title={t("admin.first_access_password")}>
            <div className="employee-choice-list">
              {PASSWORD_OPTIONS.map((option) => (
                <ChoiceOption
                  active={passwordMode === option.value}
                  description={option.description}
                  label={option.label}
                  onClick={() => setPasswordMode(option.value)}
                  key={option.value}
                />
              ))}
            </div>
          </CreateStep>
        </div>

        <footer>
          <span className={error ? "is-error" : ""}>{error || footerHint}</span>
          <div>
            <button className="secondary-button" type="button" onClick={onClose}>{t("common.cancel")}</button>
            <button className="primary-button" type="button" disabled={!canSubmit} onClick={() => void submit()}>
              {submitting ? t("admin.creating") : t("admin.create_operator")}
            </button>
          </div>
        </footer>
      </aside>
    </>
  );
}

function CreateStep({ children, number, title }: { children: ReactNode; number: string; title: string }) {
  return <section className="employee-create-step"><h3><i>{number}</i>{title}</h3>{children}</section>;
}

function CreateField({ className = "", label, mono = false, onChange, placeholder, value }: {
  className?: string;
  label: string;
  mono?: boolean;
  onChange: (value: string) => void;
  placeholder: string;
  value: string;
}) {
  return (
    <label className={`employee-create-field ${className}`}>
      <span>{label}</span>
      <input className={mono ? "mono" : ""} value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

/** Радио-вариант с описанием — роль и режим пароля (кадры E5/E6, E3). */
function ChoiceOption({ active, description, label, locked = false, onClick }: {
  active: boolean;
  description: string;
  label: string;
  locked?: boolean;
  onClick?: () => void;
}) {
  return (
    <button className={`employee-choice ${active ? "is-on" : ""} ${locked ? "is-locked" : ""}`} type="button" disabled={locked} onClick={onClick}>
      <i>{active && <span />}</i>
      <span>
        <strong>{label}{locked && <Icon name="lock" size={12} strokeWidth={1.8} />}</strong>
        <small>{description}</small>
      </span>
    </button>
  );
}
