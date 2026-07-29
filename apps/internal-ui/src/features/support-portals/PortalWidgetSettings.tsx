import { useEffect, useState } from "react";

import type { Channel } from "../channels/types";
import { SelectField } from "../../shared/form-controls";
import { Button } from "../../shared/ui-controls";
import {
  portalErrorMessage,
  updateSupportPortal,
  type SupportPortal,
} from "./model";

export function PortalWidgetSettings({
  canManage,
  channels,
  portal,
  onChanged,
}: {
  canManage: boolean;
  channels: Channel[];
  portal: SupportPortal;
  onChanged: (portal: SupportPortal) => void;
}) {
  const [channelId, setChannelId] = useState(portal.widgetChannelId);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");

  useEffect(() => setChannelId(portal.widgetChannelId), [portal.widgetChannelId]);

  async function save() {
    setBusy(true);
    setFeedback("");
    try {
      const payload = await updateSupportPortal(portal.id, {
        widgetChannelId: channelId,
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
          label="Канал виджета"
          value={String(channelId ?? "")}
          onChange={(value) => setChannelId(value ? Number(value) : null)}
          options={[
            ["", "Не показывать"],
            ...channels.map((channel): [string, string] => [
              String(channel.id),
              channel.name,
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
