import { useEffect, useState } from "react";
import { api } from "../../../api/client";
import { t } from "../../../i18n";
import { SelectField } from "../../../shared/form-controls";
import { LoadingState } from "../../../shared/ui";
import type { ServiceField } from "../services/types";

export function LookupValue({ field, value, connection, onChange }: {
  field: ServiceField; value: unknown; connection: string; onChange: (value: unknown) => void;
}) {
  const [items, setItems] = useState<Array<{ value: string | number; label: string }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true; setLoading(true); setError("");
    api<{ items: Array<{ value: string | number; label: string }> }>(`/api/v1/integrations/services/${connection}/lookups/${field.lookup}/`)
      .then(response => { if (active) setItems(response.items); })
      .catch(() => { if (active) setError(t("services.request_failed")); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [connection, field.lookup]);
  return <div className="scenario-lookup">
    <SelectField label={field.title} value={String(value ?? "")} disabled={loading || Boolean(error)} wide
      options={[["", t("scenarios.select")], ...items.map(item => [String(item.value), item.label] as [string, string])]}
      onChange={key => onChange(items.find(item => String(item.value) === key)?.value)} />
    <div className="scenario-lookup-state">{loading && <LoadingState />}{error && <span role="alert">{error}</span>}</div>
  </div>;
}
