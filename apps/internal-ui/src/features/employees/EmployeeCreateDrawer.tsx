import { useState, type ReactNode } from "react";

import { Icon } from "../../shared/icons";
import { groupColorOf } from "../conversations/model";
import type { EmployeeGroup, Role } from "../../types";
import { createEmployee, type IssuedPassword, type PasswordMode } from "./api";

// Новый сотрудник (дизайн-базлайн v2, кадры E5/E6): выезжающая панель 520px,
// четыре шага — учётные данные · роль · должность и группы · пароль.

const ROLE_OPTIONS: Array<{ value: Extract<Role, "ADMIN" | "EMPLOYEE">; label: string; description: string }> = [
  { value: "EMPLOYEE", label: "Сотрудник", description: "Работает в чате. Видит диалоги своих групп, диалоги без группы и назначенные ему." },
  { value: "ADMIN", label: "Администратор", description: "Полный доступ, идентичен владельцу. Единственное отличие владельца — его нельзя удалить." },
];

const PASSWORD_OPTIONS: Array<{ value: PasswordMode; label: string; description: string }> = [
  { value: "mail", label: "Отправить на рабочую почту", description: "Сотрудник получит письмо со ссылкой первого входа. Подходит, когда почта организации настроена и работает." },
  { value: "show", label: "Сгенерировать и показать мне", description: "Пароль покажется один раз после создания — скопируйте и передайте лично. Нужен, когда письма не доходят или ящик ещё не работает." },
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
      setError(reason instanceof Error ? reason.message : "Ошибка создания");
      setSubmitting(false);
    }
  }

  const footerHint = passwordMode === "mail"
    ? `Пароль первичного доступа отправится на ${email.trim() || "рабочую почту"}`
    : "Пароль покажем сразу после создания — скопируйте его";

  return (
    <>
      <button className="employee-drawer-scrim" type="button" aria-label="Закрыть форму" onClick={onClose} />
      <aside className="employee-create-drawer" aria-label="Новый сотрудник">
        <header>
          <div>
            <strong>Новый сотрудник</strong>
            <span>Учётные данные · роль · группы</span>
          </div>
          <button type="button" aria-label="Закрыть" onClick={onClose}><Icon name="xCircle" size={19} strokeWidth={1.8} /></button>
        </header>

        <div className="employee-create-body">
          <CreateStep number="1" title="Учётные данные">
            <div className="employee-create-grid">
              <CreateField label="Имя" value={fullName} onChange={setFullName} placeholder="Имя и фамилия" />
              <CreateField label="Телефон" value={phone} onChange={setPhone} placeholder="+7 …" />
              <CreateField className="wide" label="Рабочий email · используется для входа" value={email} onChange={setEmail} placeholder="name@company.ru" mono />
            </div>
          </CreateStep>

          <CreateStep number="2" title="Роль">
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

          <CreateStep number="3" title="Должность и группы">
            <CreateField className="is-single" label="Должность" value={positionTitle} onChange={setPositionTitle} placeholder="напр. Оператор" />
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
                          <small>{group.memberCount} сотр.</small>
                        </span>
                      </button>
                    );
                  })}
                </div>
                <p className="employee-create-note">Без групп сотрудник видит только диалоги без группы. Группы можно изменить позже.</p>
              </>
            ) : (
              <p className="employee-create-note">Групп пока нет — сотрудник будет видеть все диалоги. Группы создаются в «Настройках».</p>
            )}
          </CreateStep>

          <CreateStep number="4" title="Пароль первичного доступа">
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
            <button className="secondary-button" type="button" onClick={onClose}>Отмена</button>
            <button className="primary-button" type="button" disabled={!canSubmit} onClick={() => void submit()}>
              {submitting ? "Создание" : "Создать сотрудника"}
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
