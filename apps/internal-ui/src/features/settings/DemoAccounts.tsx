import { t } from "../../i18n";
import type { DemoAccount } from "./useDemoData";

export function DemoAccounts({ accounts }: { accounts: DemoAccount[] }) {
  return (
    <div className="settings-demo-logins">
      <small>{t("settings.sign_as_demo_operator_private")}</small>
      <div className="settings-demo-accounts">
        {accounts.map((account) => (
          <div className="settings-demo-account" key={account.email}>
            <div className="settings-demo-person">
              {account.avatarUrl
                ? <img src={account.avatarUrl} alt="" />
                : <span className="settings-demo-avatar">{account.fullName.trim().slice(0, 1).toUpperCase()}</span>}
              <span>
                <strong>{account.fullName}</strong>
                <small>{account.role === "EMPLOYEE" ? t("common.operator") : t("common.administrator")} · {account.groups.length ? account.groups.join(", ") : t("settings.no_groups")}</small>
              </span>
            </div>
            <code>{account.email}</code>
            <code>{account.password}</code>
          </div>
        ))}
      </div>
    </div>
  );
}
