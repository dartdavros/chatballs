import { useEffect, useRef, useState } from "react";

import { t } from "../../../../i18n";
import { createConnection, fetchOAuthState, replaceAccess, serviceFailure, startOAuth } from "../api";
import type { ServiceAdapter, ServiceConnection, ServiceError, ServiceField } from "../types";
import { unsupportedFields, type ServiceValues } from "./fieldControls";

export type ConnectMode = { kind: "new" } | { kind: "replace"; connection: ServiceConnection };
type Stage = "idle" | "checking" | "waiting" | "error";

const POLL_MS = 1500;

function patternErrors(fields: ServiceField[], values: ServiceValues): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const field of fields) {
    const raw = values[field.name];
    const value = typeof raw === "string" ? raw.trim() : "";
    if (value && field.pattern && !new RegExp(`^(?:${field.pattern})$`).test(value)) errors[field.name] = field.patternError ?? "";
  }
  return errors;
}

/** Состояние окна «Подключить / Восстановить доступ» (кадры модального окна Сервисы.dc.html). */
export function useConnectForm({ adapter, mode, onDone }: { adapter: ServiceAdapter; mode: ConnectMode; onDone: (id: number) => void }) {
  const isNew = mode.kind === "new";
  const [methodKey, setMethodKey] = useState(isNew ? adapter.authMethods[0]?.key ?? "" : mode.connection.authMethod);
  const [name, setName] = useState(adapter.title);
  const [values, setValues] = useState<ServiceValues>({});
  const [stage, setStage] = useState<Stage>("idle");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<ServiceError | null>(null);
  const [message, setMessage] = useState("");
  const authorizeUrl = useRef("");
  const timer = useRef<number | null>(null);
  const method = adapter.authMethods.find((item) => item.key === methodKey) ?? adapter.authMethods[0];
  const fields = [...(method?.fields ?? []), ...adapter.settings];
  const unavailable = unsupportedFields(fields);

  useEffect(() => () => { if (timer.current) window.clearInterval(timer.current); }, []);

  function fail(failure: ReturnType<typeof serviceFailure>) {
    setFieldErrors(failure.fields);
    setError(failure.error);
    setMessage(failure.message);
    setStage(failure.error ? "error" : "idle");
  }

  function watch(stateId: string) {
    timer.current = window.setInterval(async () => {
      try {
        const state = await fetchOAuthState(stateId);
        if (state.status === "pending") return;
        if (timer.current) window.clearInterval(timer.current);
        if (state.status === "completed" && state.connectionId) onDone(state.connectionId);
        else fail({ fields: {}, error: state.error, message: "" });
      } catch (failure) {
        if (timer.current) window.clearInterval(timer.current);
        fail(serviceFailure(failure));
      }
    }, POLL_MS);
  }

  async function submit() {
    if (!method || unavailable) return;
    const local = patternErrors(fields, values);
    setFieldErrors(local);
    setError(null);
    setMessage("");
    if (Object.keys(local).length) return;
    const body = { adapter: adapter.key, authMethod: method.key, name: isNew ? name : "", values };
    try {
      if (method.oauth) {
        setStage("waiting");
        const started = await startOAuth(isNew ? body : { ...body, connectionId: mode.connection.id });
        authorizeUrl.current = started.authorizeUrl;
        window.open(started.authorizeUrl, "_blank", "popup");
        watch(started.state.id);
        return;
      }
      setStage("checking");
      const connection = isNew ? await createConnection(body) : await replaceAccess(mode.connection.id, values);
      onDone(connection.id);
    } catch (failure) {
      fail(serviceFailure(failure));
    }
  }

  const busy = stage === "checking" || stage === "waiting";
  let submitLabel = isNew ? (method?.checkable ? t("services.submit_check_connect") : t("services.submit_save")) : t("services.submit_check_save");
  if (method?.oauth) submitLabel = stage === "error" ? t("services.submit_oauth_retry") : t("services.submit_oauth", { service: adapter.title });
  else if (stage === "error") submitLabel = t("services.submit_check_again");
  if (stage === "checking") submitLabel = t("services.busy_checking");
  if (stage === "waiting") submitLabel = t("services.busy_waiting");

  return {
    isNew, method, methodKey, setMethodKey, name, setName, values, fields, unavailable,
    setValue: (field: string, value: unknown) => setValues((current) => ({ ...current, [field]: value })),
    stage, busy, fieldErrors, error, message, submit, submitLabel,
    reopen: () => { if (authorizeUrl.current) window.open(authorizeUrl.current, "_blank", "popup"); },
  };
}
