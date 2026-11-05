import { Icon } from "../../shared/icons";
import type { RouteKey } from "../../types";
import { t } from "../../i18n";
import { useOnboarding } from "../onboarding/useOnboarding";
import type { TourTarget } from "../onboarding/steps";
import type { SettingsSection, SettingsSectionKey } from "./sections";

const SECTION_TOUR_TARGET: Partial<Record<SettingsSectionKey, TourTarget>> = {
  ai: "settings-ai", integrations: "settings-integrations", platform: "settings-platform",
};

export function SettingsNavigation({ mobile, hasCurrent, sections, active, counts, connectionsFailed, openSection, setRoute }: {
  mobile: boolean; hasCurrent: boolean; sections: SettingsSection[]; active: SettingsSectionKey | null;
  counts: Partial<Record<SettingsSectionKey, number>>; connectionsFailed: boolean;
  openSection: (section: SettingsSectionKey) => void; setRoute: (route: RouteKey) => void;
}) {
  const onboarding = useOnboarding();
  const links = (
    <>
      <div className="settings-subnav-divider" />
      <div className="settings-subnav-caption">{t("settings.separate_screens")}</div>
      <button className="settings-subnav-link" type="button" onClick={() => setRoute("administrationAudit")}>
        <Icon name="list" size={16} strokeWidth={1.9} /><span>{t("settings.action_audit")}</span><Icon name="external" size={13} strokeWidth={2} />
      </button>
      {/* Возврат в онбординг: он открывается в любой момент, а не только при
          первом входе. */}
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
    </>
  );

  return (
    <nav className={`settings-subnav ${mobile && hasCurrent ? "is-hidden" : ""}`}>
      <div className="settings-subnav-head"><h2>{t("common.settings")}</h2></div>
      <div className="settings-subnav-list">
        {sections.map((item) => (
          <button
            className={`settings-subnav-item ${item.key === active ? "is-active" : ""}`}
            key={item.key}
            type="button"
            data-onboarding-target={SECTION_TOUR_TARGET[item.key]}
            onClick={() => openSection(item.key)}
          >
            <Icon name={item.icon} size={16} strokeWidth={1.9} />
            <span>{item.label}</span>
            {counts[item.key] !== undefined && counts[item.key]! > 0 && <small>{counts[item.key]}</small>}
            {item.key === "integrations" && connectionsFailed && item.key !== active && <i className="settings-subnav-warn" title={t("settings.there_error")} />}
            {/* Кадр M: на узком экране у пункта — шеврон перехода. */}
            <span className="settings-subnav-chevron"><Icon name="chevronRight" size={16} strokeWidth={2} /></span>
          </button>
        ))}
        {links}
      </div>
    </nav>
  );

}
