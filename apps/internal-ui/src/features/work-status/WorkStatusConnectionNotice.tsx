import { useState } from "react";

import { t } from "../../i18n";
import { Icon } from "../../shared/icons";
import { NoticeCloseButton } from "../../shared/NoticeCloseButton";

export function WorkStatusConnectionNotice({ connectionLost }: { connectionLost: boolean }) {
  return connectionLost ? <ConnectionLostBanner /> : null;
}

function ConnectionLostBanner() {
  const [dismissed, setDismissed] = useState(false);
  if (dismissed) return null;

  return (
    <div className="notice-anchor">
      <div className="work-status-notice is-connection" role="status">
        <Icon name="refresh" size={14} />
        <span>{t("work_status.connection_lost")}</span>
        <NoticeCloseButton label={t("common.hide")} onClick={(event) => {
          event.stopPropagation();
          setDismissed(true);
        }} />
      </div>
    </div>
  );
}
