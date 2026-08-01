import { useEffect, useState } from "react";

import { SelectField } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import {
  portalErrorMessage,
  updateSupportPortal,
  type PortalWidgetOption,
  type SupportPortal,
} from "./model";

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
      const payload = await updateSupportPortal(portal.id, {
        widgetId,
      });
      onChanged(payload.portal);
      setFeedback("Веб-виджет обновлён");
    } catch (caught) {
      setFeedback(portalErrorMessage(caught, "Не удалось сохранить веб-виджет"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="portal-section">
      <div className="portal-section-heading">
        <div>
          <h2>Веб-виджет</h2>
          <p>Публичный чат отображается на всех страницах портала.</p>
        </div>
      </div>
      <div className="portal-settings-fields">
        <SelectField
          disabled={!canManage}
          label="Веб-виджет"
          value={String(widgetId ?? "")}
          onChange={(value) => setWidgetId(value ? Number(value) : null)}
          options={[
            ["", "Не показывать"],
            ...widgets.map((widget): [string, string] => [
              String(widget.id),
              widget.name,
            ]),
          ]}
        />
      </div>
      {canManage && (
        <Button variant="secondary" disabled={busy} onClick={() => void save()}>
          Сохранить виджет
        </Button>
      )}
      {feedback && <div className="portal-save-feedback">{feedback}</div>}
    </section>
  );
}
