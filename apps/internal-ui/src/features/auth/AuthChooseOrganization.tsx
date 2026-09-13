import { Icon } from "../../shared/icons";
import { roleLabel } from "../../shared/ui";
import { AuthFrame } from "./AuthFrame";
import { t } from "../../i18n";
import type { AuthenticatedUser } from "../../types";

// Выбор организации после входа — для тех, кто состоит в нескольких. Экран
// в той же матовой рамке, что вход и приглашение: список организаций
// строками «логотип · название · роль». Ссылка на конкретную организацию
// этот экран минует: адрес уже сказал, куда идти.

function initials(name: string): string {
  return name.trim().split(/\s+/).map((part) => part[0] ?? "").join("").slice(0, 2).toUpperCase() || "CB";
}

export function AuthChooseOrganization({ identity, onChoose, onLogout }: {
  identity: AuthenticatedUser;
  onChoose: (organizationPublicId: string) => void;
  onLogout: () => void;
}) {
  const logoutLink = (
    <button type="button" className="auth-back-login" onClick={onLogout}><Icon name="logout" size={14} />{t("auth.choose_organization_logout")}</button>
  );

  return (
    <AuthFrame
      title={t("auth.choose_organization_title")}
      subtitle={t("auth.choose_organization_subtitle", { name: identity.fullName || identity.email })}
      logo="pulse"
      width={420}
      note={logoutLink}
    >
      <ul className="auth-card auth-org-list">
        {identity.memberships.map((membership) => (
          <li key={membership.organizationPublicId}>
          <button
            type="button"
            className="auth-org-item"
            onClick={() => onChoose(membership.organizationPublicId)}
          >
            <span className={`auth-org-mark ${membership.organizationLogoUrl ? "has-logo" : ""}`}>
              {membership.organizationLogoUrl
                ? <img src={membership.organizationLogoUrl} alt="" />
                : initials(membership.organizationName)}
            </span>
            <span className="auth-org-copy">
              <strong>{membership.organizationName}</strong>
              <small>{membership.positionTitle || roleLabel(membership.role)}</small>
            </span>
            <Icon name="chevronRight" size={16} />
          </button>
          </li>
        ))}
      </ul>
    </AuthFrame>
  );
}
