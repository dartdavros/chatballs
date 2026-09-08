import { FormField } from "../../shared/form-controls";
import type { Integration } from "./model";

// Поля Email-подключения (SPEC-CHATBALLS-0025 §3.2): адрес + секции IMAP и SMTP.
// Порты — строками в состоянии формы; в конфиг уходят числами.
export type EmailConfigState = {
  email: string;
  imapHost: string;
  imapPort: string;
  imapSsl: boolean;
  smtpHost: string;
  smtpPort: string;
  smtpSsl: boolean;
};

export const EMAIL_CONFIG_DEFAULTS: EmailConfigState = {
  email: "",
  imapHost: "",
  imapPort: "993",
  imapSsl: true,
  smtpHost: "",
  smtpPort: "465",
  smtpSsl: true,
};

export function emailConfigFromIntegration(config: Integration["config"]): EmailConfigState {
  return {
    email: config.email || "",
    imapHost: config.imapHost || "",
    imapPort: String(config.imapPort || 993),
    imapSsl: config.imapSsl !== false,
    smtpHost: config.smtpHost || "",
    smtpPort: String(config.smtpPort || 465),
    smtpSsl: config.smtpSsl !== false,
  };
}

export function emailConfigPayload(state: EmailConfigState) {
  return {
    email: state.email.trim(),
    imapHost: state.imapHost.trim(),
    imapPort: state.imapPort.trim() ? Number(state.imapPort) : undefined,
    imapSsl: state.imapSsl,
    smtpHost: state.smtpHost.trim(),
    smtpPort: state.smtpPort.trim() ? Number(state.smtpPort) : undefined,
    smtpSsl: state.smtpSsl,
  };
}

type SectionProps = {
  title: string;
  host: string;
  port: string;
  ssl: boolean;
  hostPlaceholder: string;
  portPlaceholder: string;
  onChange: (patch: { host?: string; port?: string; ssl?: boolean }) => void;
};

function MailboxSection({ title, host, port, ssl, hostPlaceholder, portPlaceholder, onChange }: SectionProps) {
  return (
    <div className="integration-email-section">
      <h3>{title}</h3>
      <div className="integration-email-grid">
        <FormField label="Хост" mono value={host} onChange={(value) => onChange({ host: value })} placeholder={hostPlaceholder} />
        <FormField label="Порт" mono value={port} onChange={(value) => onChange({ port: value })} placeholder={portPlaceholder} />
      </div>
      <label className="integration-ssl-toggle">
        <input type="checkbox" checked={ssl} onChange={(event) => onChange({ ssl: event.target.checked })} />
        SSL/TLS
      </label>
    </div>
  );
}

export function EmailFields({ value, onChange }: { value: EmailConfigState; onChange: (value: EmailConfigState) => void }) {
  const set = (patch: Partial<EmailConfigState>) => onChange({ ...value, ...patch });
  return (
    <>
      <FormField label="Email-адрес" mono value={value.email} onChange={(email) => set({ email })} placeholder="support@company.ru" />
      <MailboxSection
        title="Входящая почта · IMAP"
        host={value.imapHost}
        port={value.imapPort}
        ssl={value.imapSsl}
        hostPlaceholder="imap.yandex.ru"
        portPlaceholder="993"
        onChange={({ host, port, ssl }) => set({ ...(host !== undefined && { imapHost: host }), ...(port !== undefined && { imapPort: port }), ...(ssl !== undefined && { imapSsl: ssl }) })}
      />
      <MailboxSection
        title="Исходящая почта · SMTP"
        host={value.smtpHost}
        port={value.smtpPort}
        ssl={value.smtpSsl}
        hostPlaceholder="smtp.yandex.ru"
        portPlaceholder="465"
        onChange={({ host, port, ssl }) => set({ ...(host !== undefined && { smtpHost: host }), ...(port !== undefined && { smtpPort: port }), ...(ssl !== undefined && { smtpSsl: ssl }) })}
      />
    </>
  );
}
