import { Modal } from "antd";
import { useCallback, useEffect, useState } from "react";

import { api } from "../../api/client";
import { Button } from "../../shared/ui-controls";
import { shortDate } from "../../shared/utils";

// Секция «Демо-данные» экрана настроек: владелец или админ ставит и удаляет
// вымышленную организацию «Ателье Норд» одной кнопкой. Работу выполняет
// worker; карточка опрашивает статус, пока идёт установка или удаление.

export type DemoStatus = "ABSENT" | "INSTALLING" | "INSTALLED" | "REMOVING" | "FAILED";

export type DemoAccount = {
  fullName: string;
  email: string;
  password: string;
  role: "OWNER" | "ADMIN" | "EMPLOYEE";
  positionTitle: string;
  groups: string[];
  avatarUrl: string | null;
};

export type DemoState = {
  status: DemoStatus;
  recordsCount: number;
  error: string;
  startedAt: string | null;
  finishedAt: string | null;
  accounts: DemoAccount[];
};

const BUSY: DemoStatus[] = ["INSTALLING", "REMOVING"];
const POLL_INTERVAL_MS = 2000;

export function demoStatusLabel(state: DemoState): string {
  switch (state.status) {
    case "INSTALLED":
      return "Установлены";
    case "INSTALLING":
      return "Устанавливаются";
    case "REMOVING":
      return "Удаляются";
    case "FAILED":
      return "Ошибка установки";
    default:
      return "Не установлены";
  }
}

export function DemoDataCard({ reload }: { reload: () => void }) {
  const [state, setState] = useState<DemoState | null>(null);
  const [error, setError] = useState("");
  const [confirmRemove, setConfirmRemove] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    try {
      setState(await api<DemoState>("/api/v1/company/demo/"));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось получить статус демо-данных");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const busy = state !== null && BUSY.includes(state.status);
  useEffect(() => {
    if (!busy) return undefined;
    const timer = window.setInterval(() => void load(), POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [busy, load]);

  // Когда работа завершилась — обновить данные приложения (сотрудники, агенты).
  const [wasBusy, setWasBusy] = useState(false);
  useEffect(() => {
    if (busy) setWasBusy(true);
    else if (wasBusy) {
      setWasBusy(false);
      reload();
    }
  }, [busy, reload, wasBusy]);

  async function install() {
    setSubmitting(true);
    setError("");
    try {
      setState(await api<DemoState>("/api/v1/company/demo/", { method: "POST" }));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось запустить установку");
    } finally {
      setSubmitting(false);
    }
  }

  async function remove() {
    setSubmitting(true);
    setError("");
    try {
      setState(await api<DemoState>("/api/v1/company/demo/", { method: "DELETE" }));
      setConfirmRemove(false);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось запустить удаление");
    } finally {
      setSubmitting(false);
    }
  }

  const label = state ? demoStatusLabel(state) : null;
  const installed = state?.status === "INSTALLED";

  return (
    <div className="administration-card">
      <div className="settings-demo-head">
        <div className="settings-demo-title">
        <strong>Ателье «Норд»</strong>
        {label && <b className={`settings-demo-status is-${state?.status.toLowerCase()}`}>{label}</b>}
        {installed && state && (
          <small>
            {state.recordsCount.toLocaleString("ru-RU")} записей
            {state.finishedAt ? ` · ${shortDate(state.finishedAt)}` : ""}
          </small>
        )}
        </div>
        <div className="settings-demo-actions">
          {!installed && (
            <Button variant="primary" disabled={busy || submitting || state === null} onClick={() => void install()}>
              {state?.status === "INSTALLING" ? "Устанавливаются…" : state?.status === "FAILED" ? "Повторить установку" : "Установить"}
            </Button>
          )}
          {(installed || state?.status === "REMOVING") && (
            <Button variant="danger-outline" disabled={busy || submitting} onClick={() => setConfirmRemove(true)}>
              {state?.status === "REMOVING" ? "Удаляются…" : "Удалить демо-данные"}
            </Button>
          )}
        </div>
      </div>
      <p className="settings-section-note">
        Сотрудники и группы, агенты с подключениями, знания, диалоги во всех состояниях, голосовые, шаблоны ответов,
        портал поддержки, звонки и уведомления. Удаляются целиком — ваши данные не затрагиваются.
      </p>
      {state?.status === "INSTALLED" && (
        <div className="settings-demo-logins">
          <small>Войдите под демо-сотрудником в приватном окне, чтобы увидеть систему его глазами:</small>
          <div className="settings-demo-accounts">
            {state.accounts.map((account) => (
              <div className="settings-demo-account" key={account.email}>
                <div className="settings-demo-person">
                  {account.avatarUrl
                    ? <img src={account.avatarUrl} alt="" />
                    : <span className="settings-demo-avatar">{account.fullName.trim().slice(0, 1).toUpperCase()}</span>}
                  <span>
                    <strong>{account.fullName}</strong>
                    <small>{account.role === "EMPLOYEE" ? "Сотрудник" : "Администратор"} · {account.groups.length ? account.groups.join(", ") : "без групп"}</small>
                  </span>
                </div>
                <code>{account.email}</code>
                <code>{account.password}</code>
              </div>
            ))}
          </div>
        </div>
      )}
      {state?.status === "FAILED" && state.error && <div className="settings-section-error">{state.error}</div>}
      {error && <div className="settings-section-error">{error}</div>}
      {confirmRemove && (
        <Modal open title="Удалить демо-данные?" onCancel={() => setConfirmRemove(false)} footer={null} destroyOnClose>
          <div className="integration-form">
            <p>Будут удалены все записи демо-набора: сотрудники, агенты, диалоги, знания и файлы. Данные, созданные вами, останутся.</p>
            {error && <div className="integration-form-error">{error}</div>}
            <div className="integration-form-actions">
              <Button variant="secondary" onClick={() => setConfirmRemove(false)}>Отмена</Button>
              <Button variant="danger-outline" disabled={submitting} onClick={() => void remove()}>Удалить</Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
