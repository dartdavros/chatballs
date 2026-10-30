import { t } from "../../../../i18n";
import type { ServiceAuthMethod } from "../types";

/** «Способ доступа» — показывается, только если адаптер предусматривает несколько. */
export function AccessMethodChooser({ methods, value, disabled, onChange }: {
  methods: ServiceAuthMethod[];
  value: string;
  disabled: boolean;
  onChange: (key: string) => void;
}) {
  if (methods.length < 2) return null;
  return (
    <div className="service-access-methods">
      <span>{t("services.access_method")}</span>
      <div>
        {methods.map((method) => (
          <button className={method.key === value ? "is-active" : ""} type="button" key={method.key} disabled={disabled} onClick={() => onChange(method.key)}>
            <strong>{method.title}</strong>
            {method.about && <small>{method.about}</small>}
          </button>
        ))}
      </div>
    </div>
  );
}
