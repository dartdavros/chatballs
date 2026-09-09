import { useEffect, useState } from "react";

import { api } from "../api/client";
import { Icon } from "../shared/icons";
import type { RouteKey, SessionUser } from "../types";
import type { SettingsSectionKey } from "../features/settings/sections";
import { t } from "../i18n";

// Блок «Запуск» в сайдбаре (SPEC-CHATBALLS-0031 §5, дизайн-базлайн v2 A1): три шага
// с автоотметкой по факту, прогресс и primary-действие текущего шага.
// «Скрыть» — предпочтение клиента (localStorage); при полном прохождении блок
// исчезает сам.

type Checklist = {
  agentCreated: boolean;
  connectionBound: boolean;
  employeeInvited: boolean;
  done: boolean;
};

type Step = {
  key: keyof Omit<Checklist, "done">;
  label: string;
  action: string;
  route: RouteKey;
  // Раздел «Настроек», если шаг ведёт в субменю (кадры N1–N7).
  section?: SettingsSectionKey;
  icon: Parameters<typeof Icon>[0]["name"];
};

const STEPS: Step[] = [
  { key: "agentCreated", label: t("profile.create_agent"), action: t("profile.create_agent"), route: "agents", icon: "robot" },
  { key: "connectionBound", label: t("profile.connect_entry_point"), action: t("profile.connect"), route: "settings", section: "integrations", icon: "plug" },
  { key: "employeeInvited", label: t("profile.invite_operators"), action: t("profile.invite"), route: "employees", icon: "team" },
];

function storageKey(user: SessionUser): string {
  return `chatballs.launch.${user.organizationPublicId}.hidden`;
}

function isHidden(user: SessionUser): boolean {
  try {
    return localStorage.getItem(storageKey(user)) === "1";
  } catch {
    return false;
  }
}

export function LaunchChecklist({ user, setRoute, openSettings }: { user: SessionUser; setRoute: (route: RouteKey) => void; openSettings: (section: SettingsSectionKey) => void }) {
  const [checklist, setChecklist] = useState<Checklist | null>(null);
  const [hidden, setHidden] = useState(() => isHidden(user));

  useEffect(() => {
    if (hidden) return;
    let cancelled = false;
    api<Checklist>("/api/v1/company/launch-checklist/")
      .then((payload) => {
        if (!cancelled) setChecklist(payload);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [hidden]);

  if (hidden || !checklist || checklist.done) return null;

  const doneCount = STEPS.filter((step) => checklist[step.key]).length;
  const current = STEPS.find((step) => !checklist[step.key]);

  function hide() {
    try {
      localStorage.setItem(storageKey(user), "1");
    } catch {
      // приватный режим — просто скрываем до перезагрузки
    }
    setHidden(true);
  }

  return (
    <div className="launch-checklist">
      <div className="launch-checklist-head">
        <div><strong>{t("profile.getting_started")}</strong><small>{t("profile.getting_started_progress", { done: doneCount, total: STEPS.length })}</small></div>
        <button aria-label={t("common.hide")} title={t("common.hide")} type="button" onClick={hide}>×</button>
      </div>
      <div className="launch-checklist-progress"><i style={{ width: `${Math.round((doneCount / STEPS.length) * 100)}%` }} /></div>
      <div className="launch-checklist-steps">
        {STEPS.map((step) => {
          const stepDone = checklist[step.key];
          const isCurrent = current?.key === step.key;
          return (
            <div className={`launch-checklist-step ${stepDone ? "is-done" : ""} ${isCurrent ? "is-current" : ""}`} key={step.key}>
              <span className="launch-checklist-mark">{stepDone && <Icon name="check" size={10} />}</span>
              <span>{step.label}</span>
            </div>
          );
        })}
      </div>
      {current && (
        <button className="launch-checklist-action" type="button" onClick={() => (current.section ? openSettings(current.section) : setRoute(current.route))}>
          <Icon name={current.icon} size={13} />
          {current.action}
        </button>
      )}
    </div>
  );
}
