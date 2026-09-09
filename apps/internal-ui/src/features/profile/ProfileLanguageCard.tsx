import { useState } from "react";

import { LANGUAGES } from "@chatballs/shared";

import { api } from "../../api/client";
import { t } from "../../i18n";
import type { AuthenticatedUser, SessionUser } from "../../types";

// «Язык» в профиле (рядом с «Внешним видом», кадр P1): личная настройка учётной
// записи, как тема и акцент. Отдельной карточкой, а не полем «Внешнего вида»:
// язык — не оформление, и человек ищет его глазами по слову, а не по разделу.
//
// Первый пункт — не язык, а отказ от выбора: «Как в организации». Сотрудник,
// который не трогал эту настройку, поедет за организацией, когда владелец
// сменит её язык; тот, кто выбрал явно, останется на своём.
//
// Подписи языков не переводятся: свой язык человек узнаёт по его собственному
// имени, и «Русский» в английском интерфейсе — именно то, что ищет глазами
// русскоязычный сотрудник.

export function ProfileLanguageCard({ user, onUserUpdated }: { user: SessionUser; onUserUpdated: (user: SessionUser) => void }) {
  const [saving, setSaving] = useState(false);
  const [errorText, setErrorText] = useState("");

  async function save(language: string) {
    if (language === user.uiLanguage) return;
    setSaving(true);
    setErrorText("");
    try {
      const payload = await api<{ user: AuthenticatedUser }>("/api/v1/auth/profile/language/", {
        method: "POST",
        body: JSON.stringify({ language }),
      });
      // Смена языка перезагружает страницу (см. src/i18n): состояние здесь
      // обновляется на случай, если язык совпал с текущим и перезагрузки нет.
      onUserUpdated({ ...user, ...payload.user });
    } catch (error) {
      setErrorText(error instanceof Error ? error.message : t("common.could_not_save"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="profile-card language-card">
      <h3>{t("profile.language")}</h3>
      <p className="profile-card-lead">{t("profile.language_lead")}</p>
      {errorText && <div className="profile-message error">{errorText}</div>}
      <div className="appearance-row">
        <span>{t("profile.interface_language")}</span>
        <div className="appearance-theme-options">
          <button
            className={user.uiLanguage === "" ? "active" : ""}
            disabled={saving}
            type="button"
            onClick={() => void save("")}
          >
            {t("profile.language_as_organization")}
          </button>
          {LANGUAGES.map((item) => (
            <button
              className={user.uiLanguage === item.code ? "active" : ""}
              disabled={saving}
              key={item.code}
              lang={item.code}
              type="button"
              onClick={() => void save(item.code)}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
