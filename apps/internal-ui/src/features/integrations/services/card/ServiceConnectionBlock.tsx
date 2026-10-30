import { useEffect, useState } from "react";

import { t } from "../../../../i18n";
import { FormField } from "../../../../shared/form-controls";
import { Button } from "../../../../shared/ui-controls";
import { accessState, authMethodOf } from "../model";
import type { ServiceAdapter, ServiceConnection } from "../types";

/** Блок «Подключение»: название, хост, способ доступа и его состояние. */
export function ServiceConnectionBlock({ connection, adapter, checking, nameError, onRename, onCheck, onReplace }: {
  connection: ServiceConnection;
  adapter: ServiceAdapter | undefined;
  checking: boolean;
  nameError?: string;
  onRename: (name: string) => void;
  onCheck: () => void;
  onReplace: () => void;
}) {
  const [name, setName] = useState(connection.name);
  useEffect(() => setName(connection.name), [connection.name]);
  const method = authMethodOf(adapter, connection);
  const commit = () => { if (name.trim() && name.trim() !== connection.name) onRename(name.trim()); };

  return (
    <section className="service-card-block">
      <h3>{t("services.connection_title")}</h3>
      <div className="service-connection-grid">
        <FormField label={t("services.name")} value={name} error={nameError} onChange={setName} onBlur={commit} />
        <div className="service-connection-host"><span>{adapter?.hostLabel}</span><div>{connection.host}</div></div>
      </div>
      <div className="service-connection-access">
        <div>
          <strong>{t("services.access", { access: method?.accessLabel ?? "" })}</strong>
          <p>{accessState(connection, method)}</p>
        </div>
        {connection.status === "unchecked" && method?.checkable && (
          <Button variant="secondary" disabled={checking} onClick={onCheck}>{checking ? t("services.busy_checking") : t("services.check_access")}</Button>
        )}
        <Button variant="secondary" onClick={onReplace}>{t("services.replace_access")}</Button>
      </div>
    </section>
  );
}
