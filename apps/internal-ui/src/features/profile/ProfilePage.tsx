import type { SessionUser } from "../../types";
import { Icon } from "../../shared/icons";
import { Avatar, PasswordField, ReadOnlyField, RoleBadge } from "../../shared/ui";

export function ProfilePage({ user, onLogout }: { user: SessionUser; onLogout: () => void }) {
  return (
    <div className="profile-stack">
      <section className="profile-header-card">
        <Avatar user={user} />
        <div className="profile-header-main">
          <div><h1>{user.fullName || user.email}</h1><RoleBadge role={user.role} /></div>
          <p>{user.email}</p>
        </div>
        <button className="danger-outline" onClick={onLogout}><Icon name="logout" size={15} />Выйти</button>
      </section>
      <section className="profile-card">
        <h3>Личные данные</h3>
        <div className="profile-grid">
          <ReadOnlyField label="Имя" value={user.fullName || user.email} editable />
          <ReadOnlyField label="Email · используется для входа" value={user.email} editable mono />
          <ReadOnlyField label="Роль" value={user.role} />
        </div>
        <div className="profile-actions"><button className="primary-button">Сохранить</button></div>
      </section>
      <section className="profile-card">
        <h3>Смена пароля</h3>
        <div className="password-fields">
          <PasswordField label="Текущий пароль" value="········" />
          <PasswordField label="Новый пароль" placeholder="мин. 10 символов" />
          <PasswordField label="Повторите новый пароль" />
        </div>
        <div className="profile-actions"><button className="secondary-button">Обновить пароль</button></div>
      </section>
      <section className="profile-card totp-card">
        <div>
          <h3>Двухфакторная аутентификация (TOTP)</h3>
          <p>{user.totpEnabled ? "Включена. Для OWNER рекомендуется держать включённой." : "Отключена. Для роли OWNER настоятельно рекомендуется включить."}</p>
        </div>
        <span className={`totp-switch ${user.totpEnabled ? "on" : ""}`}><i /></span>
        {user.totpEnabled && <div className="security-note ok">Приложение-аутентификатор подключено · последний код принят 5 мин назад</div>}
      </section>
      <section className="sessions-card">
        <div className="sessions-head"><h3>Активные сессии</h3><button>Завершить другие сессии</button></div>
        <div className="session-row"><span className="session-icon"><Icon name="user" /></span><span><strong>Браузер</strong><small>сейчас активна</small></span><b>текущая</b></div>
      </section>
    </div>
  );
}
