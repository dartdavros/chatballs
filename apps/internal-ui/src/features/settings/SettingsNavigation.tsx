import { t } from "../../i18n";
import { Icon } from "../../shared/icons";
import type { RouteKey, SessionUser } from "../../types";
import { useOnboarding } from "../onboarding/useOnboarding";
import type { TourTarget } from "../onboarding/steps";
import { visibleSettingsGroups } from "./navigation";
import type { SettingsSectionKey } from "./sections";
import "./navigation.css";

const SECTION_TOUR_TARGET: Partial<Record<SettingsSectionKey, TourTarget>> = {
  platform: "settings-platform",
};

export function SettingsNavigation({ user, active, hidden, counts, openSection, setRoute }: {
  user: SessionUser;
  active: SettingsSectionKey | null;
  hidden: boolean;
  counts: Partial<Record<SettingsSectionKey, number>>;
  openSection: (section: SettingsSectionKey) => void;
  setRoute: (route: RouteKey) => void;
}) {
  const onboarding = useOnboarding();
  return (
    <nav className={`settings-subnav ${hidden ? "is-hidden" : ""}`} aria-label={t("common.settings")}>
      <div className="settings-subnav-head"><h2>{t("common.settings")}</h2></div>
      <div className="settings-subnav-list">
        {visibleSettingsGroups(user).map(group => (
          <div className="settings-subnav-group" key={group.key} role="group" aria-labelledby={`settings-group-${group.key}`}>
            <div className="settings-subnav-caption settings-subnav-group-caption" id={`settings-group-${group.key}`}>{group.label}</div>
            {group.sections.map(item => (
              <button
                className={`settings-subnav-item ${item.key === active ? "is-active" : ""}`}
                key={item.key}
                type="button"
                aria-current={item.key === active ? "page" : undefined}
                data-onboarding-target={SECTION_TOUR_TARGET[item.key]}
                onClick={() => openSection(item.key)}
              >
                <Icon name={item.icon} size={16} strokeWidth={1.9} />
                <span>{item.label}</span>
                {counts[item.key] !== undefined && counts[item.key]! > 0 && <small>{counts[item.key]}</small>}
                <span className="settings-subnav-chevron"><Icon name="chevronRight" size={16} strokeWidth={2} /></span>
              </button>
            ))}
          </div>
        ))}
        <div className="settings-subnav-divider" />
        <div className="settings-subnav-caption">{t("settings.separate_screens")}</div>
        <button className="settings-subnav-link" type="button" onClick={() => setRoute("administrationAudit")}>
          <Icon name="list" size={16} strokeWidth={1.9} /><span>{t("settings.action_audit")}</span><Icon name="external" size={13} strokeWidth={2} />
        </button>
        {onboarding?.available && (
          <>
            <div className="settings-subnav-divider" />
            <button className="settings-subnav-onboarding" type="button" onClick={onboarding.open}>
              <Icon name="sparkles" size={16} strokeWidth={1.9} />
              <span>{t("onboarding.title")}</span>
              <small>{t("onboarding.progress_short", { done: onboarding.doneCount, total: onboarding.steps.length })}</small>
            </button>
            <p className="settings-subnav-onboarding-note">{t("onboarding.settings_hint")}</p>
          </>
        )}
      </div>
    </nav>
  );
}
