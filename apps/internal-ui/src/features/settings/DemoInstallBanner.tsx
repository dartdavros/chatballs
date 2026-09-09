import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "../../api/client";
import { Icon, LogoSpinner } from "../../shared/icons";
import type { DemoState } from "./DemoDataCard";
import { t } from "../../i18n";

// Полоса поверх рабочей области, пока worker ставит демо-данные. Без неё
// человек, поставивший галочку в мастере, видит пустую систему и не понимает,
// что установка ещё идёт (запись в outbox, разбор — секунды, но не мгновение).

const POLL_INTERVAL_MS = 2000;

export function DemoInstallBanner({ reload }: { reload: () => void }) {
  const [status, setStatus] = useState<DemoState["status"] | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const wasInstalling = useRef(false);

  const load = useCallback(async () => {
    try {
      const state = await api<DemoState>("/api/v1/company/demo/");
      setStatus(state.status);
    } catch {
      // Нет прав или сеть моргнула — полоса просто не показывается.
      setStatus("ABSENT");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const installing = status === "INSTALLING";
  useEffect(() => {
    if (!installing) return undefined;
    wasInstalling.current = true;
    const timer = window.setInterval(() => void load(), POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [installing, load]);

  // Установка закончилась — подтянуть сотрудников, группы и агентов сразу.
  useEffect(() => {
    if (status === "INSTALLED" && wasInstalling.current) reload();
  }, [reload, status]);

  if (dismissed) return null;
  if (installing) {
    return (
      <div className="demo-install-banner">
        <LogoSpinner size={17} />
        <span>{t("settings.demo_data_being_installed_sections")}</span>
      </div>
    );
  }
  if (status === "INSTALLED" && wasInstalling.current) {
    return (
      <div className="demo-install-banner is-done">
        <Icon name="check" size={15} strokeWidth={2.2} />
        <span>{t("settings.demo_data_ready")}</span>
        <button type="button" onClick={() => window.location.reload()}>{t("common.show")}</button>
        <button className="demo-install-close" type="button" onClick={() => setDismissed(true)} aria-label={t("common.hide")}>
          <Icon name="close" size={14} strokeWidth={2} />
        </button>
      </div>
    );
  }
  return null;
}
