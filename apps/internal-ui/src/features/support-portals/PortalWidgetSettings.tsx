import { useEffect, useState } from "react";

import { Icon } from "../../shared/icons";
import { Button } from "../../shared/ui-controls";
import {
  portalErrorMessage,
  updateSupportPortal,
  type PortalWidgetOption,
  type SupportPortal,
} from "./model";
import { t } from "../../i18n";

export function PortalWidgetSettings({
  canManage,
  widgets,
  portal,
  onChanged,
}: {
  canManage: boolean;
  widgets: PortalWidgetOption[];
  portal: SupportPortal;
  onChanged: (portal: SupportPortal) => void;
}) {
  const [widgetId, setWidgetId] = useState(portal.widgetId);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");

  useEffect(() => setWidgetId(portal.widgetId), [portal.widgetId]);

  async function save() {
    setBusy(true);
    setFeedback("");
    try {
      const payload = await updateSupportPortal(portal.id, { widgetId });
      onChanged(payload.portal);
      setFeedback(t("portals.web_widget_updated"));
    } catch (caught) {
      setFeedback(portalErrorMessage(caught, t("portals.could_not_save_web_widget")));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="portal-settings-card">
      <label className="portal-field is-narrow">
        <span className="portal-field-label">{t("common.web_widget_2")}</span>
        <span className="portal-select">
          <select
            disabled={!canManage}
            value={String(widgetId ?? "")}
            onChange={(event) => setWidgetId(event.target.value ? Number(event.target.value) : null)}
          >
            <option value="">{t("portals.do_not_show")}</option>
            {widgets.map((widget) => <option key={widget.id} value={widget.id}>{widget.name}</option>)}
          </select>
          <Icon name="chevron" size={14} strokeWidth={2} />
        </span>
        <small>{t("portals.widget_available_anonymous_portal_visitors")}</small>
      </label>
      {canManage && (
        <div className="portal-settings-actions">
          <Button variant="primary" disabled={busy} onClick={() => void save()}>{t("portals.save_widget")}</Button>
          {feedback && <span className="portal-settings-note">{feedback}</span>}
        </div>
      )}
    </div>
  );
}
