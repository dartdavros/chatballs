import { Modal } from "antd";

import { t } from "../../../../i18n";
import { Icon, LogoSpinner } from "../../../../shared/icons";
import { Button } from "../../../../shared/ui-controls";
import { ServiceLogo } from "../ServiceLogo";
import type { ServiceAdapter } from "../types";
import { AccessMethodChooser } from "./AccessMethodChooser";
import { ConnectHelpPanel } from "./ConnectHelpPanel";
import { ServiceAlert } from "./ServiceAlert";
import { OAuthWaiting } from "./OAuthWaiting";
import { SchemaFields } from "./SchemaFields";
import { type ConnectMode, useConnectForm } from "./useConnectForm";
import { FormField } from "../../../../shared/form-controls";

// Окно «Подключить {сервис}» / «Восстановить доступ к {сервис}» (Сервисы.dc.html,
// кадры «· форма», «· неверная ссылка», «· нет доступа», «· вход», «· токен»).
export function ServiceConnectModal({ adapter, mode, onClose, onDone }: {
  adapter: ServiceAdapter;
  mode: ConnectMode;
  onClose: () => void;
  onDone: (connectionId: number) => void;
}) {
  const form = useConnectForm({ adapter, mode, onDone });
  const method = form.method;
  const withHelp = Boolean(adapter.help) && !method?.oauth;
  const title = form.isNew ? t("services.connect_title", { service: adapter.title }) : t("services.restore_title", { service: adapter.title });
  const lead = form.isNew ? adapter.connectLead : t("services.restore_lead");
  const hint = method?.oauth ? "" : method?.checkable ? method.checkNote : t("services.saved_without_check");

  return (
    <Modal className="service-connect-modal" open onCancel={onClose} footer={null} title={null} closable={false} width={withHelp ? 760 : 600} centered destroyOnHidden>
      <header className="service-connect-head">
        <div><h3>{title}</h3><p>{lead}</p></div>
        <ServiceLogo adapter={adapter} height={20} />
        <button className="service-connect-close" type="button" title={t("services.close")} aria-label={t("services.close")} onClick={onClose}><Icon name="close" size={16} /></button>
      </header>
      <div className="service-connect-body">
        {form.error && <ServiceAlert tone="error" title={form.error.title} text={form.error.text} />}
        {form.message && <ServiceAlert tone="error" title={form.message} text="" />}
        {form.unavailable && <ServiceAlert tone="error" title={t("services.request_failed")} text="" />}
        {form.isNew && <AccessMethodChooser methods={adapter.authMethods} value={form.methodKey} disabled={form.busy} onChange={form.setMethodKey} />}
        <div className={withHelp ? "service-connect-grid" : "service-connect-stack"}>
          <div className="service-connect-fields">
            {form.isNew && !method?.oauth && (
              <div className="service-field">
                <FormField label={t("services.name_label")} value={form.name} disabled={form.busy} error={form.fieldErrors.name} wide onChange={form.setName} />
                <small>{t("services.name_hint")}</small>
              </div>
            )}
            {method && <SchemaFields fields={form.fields} values={form.values} errors={form.fieldErrors} disabled={form.busy} onChange={form.setValue} />}
            {method?.oauth && form.stage === "waiting" && <OAuthWaiting service={adapter.title} onReopen={form.reopen} />}
            {method?.oauth && method.note && <p className="service-connect-note">{method.note}</p>}
          </div>
          {withHelp && adapter.help && <ConnectHelpPanel help={adapter.help} />}
        </div>
      </div>
      <footer className="service-connect-foot">
        <span>{hint}</span>
        <div>
          <Button variant="secondary" onClick={onClose}>{t("services.cancel")}</Button>
          <Button variant="primary" disabled={form.busy || form.unavailable} onClick={() => void form.submit()}>
            {form.busy && <LogoSpinner size={14} />}{form.submitLabel}
          </Button>
        </div>
      </footer>
    </Modal>
  );
}
