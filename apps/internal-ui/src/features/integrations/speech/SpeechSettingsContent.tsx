import { t } from "../../../i18n";
import { FormField } from "../../../shared/form-controls";
import { BackLink, Button } from "../../../shared/ui-controls";
import { LogoSpinner } from "../../../shared/icons";
import { StatusPill } from "../../../shared/ui";
import type { Integration } from "../model";
import { useSpeechConnection } from "./useSpeechConnection";
import "../../administration/styles.css";
import "./speech-settings.css";

export function SpeechSettingsContent({ initial, onBack, onSaved }: { initial: Integration | null; onBack: () => void; onSaved: () => void }) {
  const form = useSpeechConnection(initial, onSaved);
  const status = form.dirty ? "UNCHECKED" : form.connection?.status ?? "UNCHECKED";
  return <>
    <BackLink label={t("common.connections")} onClick={onBack} />
    <header className="settings-head"><div><h2>Yandex SpeechKit</h2></div></header>
    <div className="administration-card server-form speech-connection">
      <p>{t("speech.connectHelp")}</p>
      <div className="administration-fields speech-connection-fields">
        <FormField label={t("speech.name")} value={form.name} onChange={form.setName} error={form.fields.name} disabled={form.busy || form.checking} />
        <FormField label={t("speech.folder")} value={form.folder} onChange={form.setFolder} error={form.fields.folder} disabled={form.busy || form.checking} />
        <div className="administration-field-wide">
          <FormField label={t("speech.secret")} value={form.secret} onChange={form.setSecret} type="password" placeholder={form.connection?.hasSecret ? "••••••••••••" : ""} error={form.fields.secret} disabled={form.busy || form.checking} />
          <small className="settings-section-note">{t("speech.secretHelp")}</small>
        </div>
      </div>
      <p className="settings-section-note">{t("speech.privacy")}</p>
      <div className="speech-check">
        <strong>{t("speech.stt")}</strong>
        <div role="status" className="speech-check-status">{form.checkingCapability === "stt" ? <LogoSpinner size={20} /> : <StatusPill status={status === "OK" ? "healthy" : status === "ERROR" ? "error" : "unchecked"} label={t(status === "OK" ? "speech.available" : status === "ERROR" ? "speech.unavailable" : "ai.not_checked")} />}</div>
        <Button variant="secondary" disabled={form.dirty || form.busy || form.checking} onClick={() => void form.check()}>{t("speech.checkStt")}</Button>
      </div>
      <div className="speech-check">
        <strong>{t("speech.tts")}</strong>
        <div role="status" className="speech-check-status">{form.checkingCapability === "tts" ? <LogoSpinner size={20} /> : <StatusPill
          status={form.connection?.ttsCheck?.status === "OK" && !form.dirty ? "healthy" : form.connection?.ttsCheck?.status === "ERROR" && !form.dirty ? "error" : "unchecked"}
          label={t(!form.dirty && form.connection?.ttsCheck?.status === "OK" ? "speech.available" : !form.dirty && form.connection?.ttsCheck?.status === "ERROR" ? "speech.unavailable" : "ai.not_checked")} />}</div>
        <Button variant="secondary" disabled={Boolean(form.dirty || form.busy || form.checking)} onClick={() => void form.check("tts")}>{t("speech.checkTts")}</Button>
      </div>
      {(form.error || (!form.dirty && form.connection?.lastError)) && <div className="administration-message error" role="alert">{form.error || form.connection?.lastError}</div>}
      <div className="administration-actions"><Button variant="primary" disabled={form.busy || form.checking} onClick={() => void form.save()}>{form.busy ? t("ai.saving") : form.connection ? t("common.save") : t("speech.connect")}</Button></div>
    </div>
  </>;
}
