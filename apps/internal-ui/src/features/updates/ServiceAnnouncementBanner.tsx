import { useState } from "react";

import { t } from "../../i18n";
import { Icon } from "../../shared/icons";
import type { ServiceAnnouncement } from "./useExternalChecks";
import "./service-announcement.css";

function safeLink(value: string): boolean {
  const authority = value.match(/^https?:\/\/([^/?#]+)/i)?.[1];
  if (!authority || authority.includes("@") || /[\s\\\p{Cc}]/u.test(value)) return false;
  try {
    return Boolean(new URL(value).hostname);
  } catch {
    return false;
  }
}

export function ServiceAnnouncementBanner({ announcements, onDismissLast }: {
  announcements: ServiceAnnouncement[] | null;
  onDismissLast: () => void;
}) {
  const [dismissed, setDismissed] = useState<ReadonlySet<number>>(() => new Set());
  const remaining = announcements?.filter(({ id }) => !dismissed.has(id));
  const message = remaining?.[0];
  if (!message) return null;

  function dismiss(id: number) {
    setDismissed((current) => new Set(current).add(id));
    if (!remaining?.some((item) => item.id !== id)) onDismissLast();
  }

  const close = t("common.close");
  return (
    <section className="demo-install-banner service-announcement" aria-label={t("updates.announcement_label")}>
      <div className="service-announcement-content" aria-live="polite">
        <Icon name="info" size={15} strokeWidth={2} />
        <span className="service-announcement-text">
          <strong>{message.title}</strong>{" "}{message.text}
        </span>
        {safeLink(message.link) && (
          <a className="link is-neutral has-icon" href={message.link} target="_blank" rel="noreferrer">
            {t("updates.announcement_details")}
            <Icon name="external" size={13} strokeWidth={2} />
          </a>
        )}
      </div>
      <button className="demo-install-close" type="button" aria-label={close} title={close} onClick={() => dismiss(message.id)}>
        <Icon name="close" size={14} strokeWidth={2} />
      </button>
    </section>
  );
}
