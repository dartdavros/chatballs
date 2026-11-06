import { useState } from "react";
import { fmt, t } from "../../../../i18n";
import { SwitchButton } from "../../../../shared/form-controls";
import { LoadingState } from "../../../../shared/ui";
import { Button } from "../../../../shared/ui-controls";
import { ExchangeDrawer } from "../../scenarios/ExchangeDrawer";
import type { ServiceAdapter, ServiceConnection } from "../types";
import { useServiceExchange } from "./useServiceExchange";
import "../../scenarios/scenarios.css";
import "./exchange.css";

export function ServiceExchangeBlock({ connection, adapter }: { connection: ServiceConnection; adapter: ServiceAdapter }) {
  const state = useServiceExchange(connection.id);
  const [open, setOpen] = useState(false);
  const enabled = state.settings?.definition.synchronization.some(p => p.enabled) ?? false;
  if (!adapter.entities?.some(entity => entity.synchronization?.directions.length)) return null;
  return <section className="service-card-block service-exchange-block"><h3>{t("scenarios.exchange_title")}</h3>
    <p className="service-card-lead">{t("scenarios.exchange_lead")}</p>
    {state.loading ? <LoadingState /> : !state.settings || !state.catalog ? <div role="alert">{state.error}<button className="link" type="button" onClick={() => void state.reload()}>{t("scenarios.reload")}</button></div>
      : <div className="service-exchange-tools">
        {state.settings.revision > 0 && <SwitchButton className="ui-switch is-compact" label={t("scenarios.sync_enable")} checked={enabled}
          disabled={state.saving} onClick={() => { if (enabled) void state.save({ ...state.settings!, definition: { ...state.settings!.definition, synchronization: state.settings!.definition.synchronization.map(p => ({ ...p, enabled: false })) } }); else setOpen(true); }} />}
        <Button variant="secondary" disabled={state.saving} onClick={() => setOpen(true)}>{t("scenarios.exchange_configure")}</Button>
      </div>}
    {state.error && state.settings && !open && <p className="service-card-lead" role="alert">{state.error}</p>}
    <p className="service-exchange-status" role={state.settings?.error ? "alert" : undefined}>{state.settings?.error ||
      (state.settings?.result ? `${state.settings.result.stateLabel}${state.settings.result.finishedAt ? ` · ${fmt.shortDateTime(state.settings.result.finishedAt)}` : ""}` : "")}</p>
    {open && state.settings && state.catalog && <ExchangeDrawer connection={connection} adapter={adapter.key} catalog={state.catalog}
      settings={state.settings} saving={state.saving} error={state.error} onSave={state.save} onClose={() => setOpen(false)} />}
  </section>;
}
