import { useEffect, useState } from "react";
import { api } from "../../../api/client";
import { t } from "../../../i18n";
import { SelectField } from "../../../shared/form-controls";
import { LoadingState } from "../../../shared/ui";
import type { ServiceField } from "../services/types";
import type { Mapping } from "./types";

type Option = { value: string | number | boolean; label: string };
export function ExchangeValues({ source, target, connection, value, onChange }: {
  source: ServiceField; target: ServiceField; connection: number; value: Mapping; onChange: (mapping: Mapping) => void;
}) {
  const [options, setOptions] = useState<[Option[], Option[]]>([[], []]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let active = true; setLoading(true); setFailed(false);
    const load = (field: ServiceField) => field.lookup ? api<{ items: Option[] }>(`/api/v1/integrations/services/${connection}/lookups/${field.lookup}/`).then(r => r.items) : Promise.resolve(field.options ?? []);
    Promise.all([load(source), load(target)]).then(result => { if (active) setOptions(result); })
      .catch(() => { if (active) setFailed(true); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [source, target, connection]);
  return <div className="exchange-value-map">
    <strong>{t(value.direction === "forward" ? "scenarios.exchange_values_forward" : "scenarios.exchange_values_reverse")}</strong>
    {loading ? <LoadingState /> : failed ? <p role="alert">{t("services.request_failed")}</p> : options[0].map((option, index) => {
      const selected = value.values?.find(v => v.from === option.value)?.to;
      return <div className="exchange-map-row" key={index}><span>{option.label}</span><span>→</span>
        <SelectField label={target.title} value={String(options[1].findIndex(v => v.value === selected))} options={[["-1", t("scenarios.exchange_no_change")], ...options[1].map((v, i) => [String(i), v.label] as [string, string])]}
          onChange={next => onChange({ ...value, values: [...(value.values ?? []).filter(v => v.from !== option.value), { from: option.value, to: options[1][Number(next)]?.value ?? null }] })} wide />
      </div>;
    })}
  </div>;
}
