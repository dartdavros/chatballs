import { useState } from "react";

import { Icon } from "../../shared/icons";
import { Avatar } from "../../shared/ui";
import { CopyButton } from "../../shared/ui-controls";
import { resetEmployeePassword, type IssuedPassword } from "./api";
import { employeeAvatarColor } from "./model";

// Пароль первичного доступа (дизайн-базлайн v2, кадры E7/E8). Показывается один
// раз: сервер отдал его в ответе и хранит только хеш.

const TITLES = {
  created: { title: "Сотрудник создан", sub: "Пароль сгенерирован и показан один раз — скопируйте его сейчас." },
  reset: { title: "Пароль сброшен", sub: "Активные сессии сотрудника завершены, при первом входе он задаст свой пароль." },
} as const;

export function EmployeePasswordDialog({ issued, onClose }: { issued: IssuedPassword; onClose: () => void }) {
  const [masked, setMasked] = useState(false);
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const { title, sub } = TITLES[issued.reason];
  const employee = issued.employee;

  async function sendByMail() {
    setSending(true);
    setError("");
    try {
      await resetEmployeePassword(employee.id, "mail");
      setSent(true);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось отправить письмо");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="employee-dialog-scrim">
      <section className="employee-password-dialog" role="dialog" aria-label={title}>
        <header>
          <i><Icon name="lock" size={20} strokeWidth={1.9} /></i>
          <div>
            <h2>{title}</h2>
            <p>{sub}</p>
          </div>
        </header>
        <div className="employee-password-body">
          <div className="employee-password-person">
            <Avatar employee={employee} background={employeeAvatarColor(employee)} />
            <span>
              <strong>{employee.fullName || employee.email}</strong>
              <small>{employee.email}</small>
            </span>
          </div>
          <label className="employee-password-field">
            <span>Пароль первичного доступа</span>
            <span className="employee-password-value">
              <code>{masked ? "•".repeat(issued.password.length) : issued.password}</code>
              <button className="employee-password-mask" type="button" title={masked ? "Показать" : "Скрыть"} aria-label={masked ? "Показать" : "Скрыть"} onClick={() => setMasked((value) => !value)}>
                <Icon name={masked ? "eyeOff" : "eye"} size={16} strokeWidth={1.8} />
              </button>
              <CopyButton className="employee-password-copy" label="Копировать" value={issued.password} />
            </span>
          </label>
          <div className="employee-password-warning">
            <Icon name="warning" size={17} strokeWidth={1.9} />
            <p>Пароль показывается один раз и на сервере не хранится в открытом виде. Скопируйте и передайте сотруднику лично — при первом входе он сменит его сам. Если окно закрыть, останется только сбросить пароль заново.</p>
          </div>
          <button className="employee-password-mail" type="button" disabled={sending || sent} onClick={() => void sendByMail()}>
            <Icon name="mail" size={14} strokeWidth={1.8} />
            {sent ? "Письмо отправлено" : sending ? "Отправка…" : "Отправить на почту вместо этого"}
          </button>
          {error && <div className="employees-error"><Icon name="alert" size={16} strokeWidth={1.8} />{error}</div>}
        </div>
        <footer>
          <small>Действие записано в аудит</small>
          <button className="primary-button employee-dialog-primary" type="button" onClick={onClose}>Скопировал, закрыть</button>
        </footer>
      </section>
    </div>
  );
}
