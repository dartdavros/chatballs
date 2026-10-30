import { t } from "../../../../i18n";
import type { ServiceAdapter } from "../types";

// Блок «Сценарии» карточки: готовые сценарии адаптера. Кнопки «Настроить» /
// «Изменить» и ссылки на раздел «Сценарии» появятся вместе с редактором
// сценариев (решение владельца по T-168).
export function ServicePresetsBlock({ adapter }: { adapter: ServiceAdapter }) {
  if (!adapter.presets.length) return null;
  return (
    <section className="service-card-block service-presets">
      <h3>{t("services.scenarios_title")}</h3>
      <p className="service-card-lead">{t("services.scenarios_lead", { service: adapter.title })}</p>
      {adapter.presets.map((preset) => (
        <div className="service-preset" key={preset.key}>
          <div>
            <div className="service-preset-name"><strong>{preset.title}</strong><span>{t("services.preset_tag")}</span></div>
            <p>{preset.purpose}</p>
          </div>
          <span className="service-preset-state">{t("services.preset_not_set")}</span>
        </div>
      ))}
    </section>
  );
}
