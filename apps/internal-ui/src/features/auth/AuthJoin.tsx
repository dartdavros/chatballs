import { useEffect, useState } from "react";

import { api } from "../../api/client";
import { Icon } from "../../shared/icons";
import { AuthFrame } from "./AuthFrame";
import { t } from "../../i18n";
import type { AuthenticatedUser } from "../../types";

// Приглашение в организацию по ссылке из письма (/join?token=…): человек уже
// вошёл под своей учётной записью, приглашение принимается само, и приложение
// открывается в новой организации. Отказ сервера показывается его же словами.

type Status = "accepting" | "failed";

export function AuthJoin({ token, onAccepted, onBack }: {
  token: string;
  onAccepted: (user: AuthenticatedUser, organizationPublicId: string) => void;
  onBack: () => void;
}) {
  const [status, setStatus] = useState<Status>("accepting");
  const [detail, setDetail] = useState("");

  useEffect(() => {
    let active = true;
    api<{ user: AuthenticatedUser; organizationPublicId: string }>("/api/v1/auth/invitations/accept/", {
      method: "POST",
      body: JSON.stringify({ token }),
    })
      .then((payload) => { if (active) onAccepted(payload.user, payload.organizationPublicId); })
      .catch((error) => {
        if (!active) return;
        setDetail(error instanceof Error ? error.message : "");
        setStatus("failed");
      });
    return () => { active = false; };
  }, [token, onAccepted]);

  if (status === "accepting") {
    return (
      <AuthFrame title={t("auth.invitation_title")} subtitle={t("admin.one_moment")} logo="shield">
        <div className="auth-card"><p className="auth-hint">{t("auth.invitation_accepting")}</p></div>
      </AuthFrame>
    );
  }

  const backLink = (
    <button type="button" className="auth-back-login" onClick={onBack}><Icon name="arrow" size={14} />{t("profile.go_start_page")}</button>
  );

  return (
    <AuthFrame title={t("auth.invitation_title")} subtitle={t("auth.invitation_not_accepted")} logo="shield" note={backLink}>
      <div className="auth-card">
        <div className="auth-recovery-sent">
          <div className="auth-recovery-sent-icon warning"><Icon name="warning" size={26} /></div>
          <h3>{t("auth.invitation_not_accepted")}</h3>
          {detail && <p>{detail}</p>}
        </div>
      </div>
    </AuthFrame>
  );
}
