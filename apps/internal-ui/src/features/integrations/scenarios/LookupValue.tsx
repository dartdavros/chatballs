import { useEffect, useState } from "react";
import { ApiError } from "../../../api/client";
import { serviceFailure } from "../services/api";
import { useLookupAccess } from "../services/lookupAccess";
import { t } from "../../../i18n";
import { SelectField } from "../../../shared/form-controls";
import { LoadingState } from "../../../shared/ui";
import type { ServiceField } from "../services/types";

export function LookupValue({ field, value, connection, onChange, error: validationError }: {
  field: ServiceField; value: unknown; connection: string; onChange: (value: unknown) => void;
  error?: string;
}) {
  const [items, setItems] = useState<Array<{ value: string | number; label: string }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useLookupAccess();
  useEffect(() => {
    let active = true; setLoading(true); setError("");
    load(connection, field.lookup ?? "")
      .then(items => { if (active) setItems(items); })
      .catch(error => {
        const failure = serviceFailure(error);
        if (active) setError(failure.error ? `${failure.error.title} ${failure.error.text}` : error instanceof ApiError ? error.message : t("services.request_failed"));
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [connection, field.lookup, load]);
  return <div className="scenario-lookup">
    <SelectField label={field.title} value={String(value ?? "")} disabled={loading || Boolean(error)} invalid={Boolean(error || validationError)} wide
      options={[["", t("scenarios.select")], ...items.map(item => [String(item.value), item.label] as [string, string])]}
      onChange={key => onChange(items.find(item => String(item.value) === key)?.value)} />
    <div className="scenario-lookup-state">{loading && <LoadingState variant="inline" />}{(error || validationError) && <span role="alert">{error || validationError}</span>}</div>
  </div>;
}
