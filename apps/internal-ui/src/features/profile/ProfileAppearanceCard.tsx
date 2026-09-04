import { useState } from "react";

import { api } from "../../api/client";
import { ACCENT_PRESETS, DEFAULT_ACCENT, type UiTheme } from "../../shared/appearance";
import type { AuthenticatedUser, SessionUser } from "../../types";

// «Внешний вид» (SPEC-HUB-0031 §7): тема (светлая/тёмная/системная) и акцентный
// цвет — пресеты плюс произвольный HEX. Настройка глобальная для пользователя;
// применение мгновенное через App (uiTheme/uiAccent в session-payload).

const THEME_OPTIONS: Array<[UiTheme, string]> = [
  ["LIGHT", "Светлая"],
  ["DARK", "Тёмная"],
  ["SYSTEM", "Как в системе"],
];

export function ProfileAppearanceCard({ user, onUserUpdated }: { user: SessionUser; onUserUpdated: (user: SessionUser) => void }) {
  const [saving, setSaving] = useState(false);
  const [errorText, setErrorText] = useState("");
  const [customAccent, setCustomAccent] = useState(
    ACCENT_PRESETS.some(([value]) => value === (user.uiAccent || DEFAULT_ACCENT)) ? "" : user.uiAccent,
  );

  const accent = user.uiAccent || DEFAULT_ACCENT;

  async function save(theme: UiTheme, nextAccent: string) {
    setSaving(true);
    setErrorText("");
    try {
      const payload = await api<{ user: AuthenticatedUser }>("/api/v1/auth/profile/appearance/", {
        method: "POST",
        body: JSON.stringify({ theme, accent: nextAccent }),
      });
      onUserUpdated({ ...user, ...payload.user });
    } catch (error) {
      setErrorText(error instanceof Error ? error.message : "Не удалось сохранить");
    } finally {
      setSaving(false);
    }
  }

  function submitCustomAccent() {
    const value = customAccent.trim().toLowerCase();
    if (!/^#[0-9a-f]{6}$/.test(value)) {
      setErrorText("Свой цвет — HEX вида #1677ff");
      return;
    }
    void save(user.uiTheme, value);
  }

  return (
    <section className="profile-card appearance-card">
      <h3>Внешний вид</h3>
      {errorText && <div className="profile-message">{errorText}</div>}
      <div className="appearance-row">
        <span>Тема</span>
        <div className="appearance-theme-options">
          {THEME_OPTIONS.map(([value, label]) => (
            <button
              className={user.uiTheme === value ? "active" : ""}
              disabled={saving}
              key={value}
              type="button"
              onClick={() => void save(value, user.uiAccent)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      <div className="appearance-row">
        <span>Акцентный цвет</span>
        <div className="appearance-accents">
          {ACCENT_PRESETS.map(([value, label]) => (
            <button
              aria-label={label}
              className={accent === value ? "active" : ""}
              disabled={saving}
              key={value}
              style={{ background: value }}
              title={label}
              type="button"
              onClick={() => void save(user.uiTheme, value)}
            />
          ))}
          <div className="appearance-custom">
            <input
              disabled={saving}
              maxLength={7}
              placeholder="#1677ff"
              value={customAccent}
              onChange={(event) => setCustomAccent(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") submitCustomAccent();
              }}
            />
            <button disabled={saving || !customAccent.trim()} type="button" onClick={submitCustomAccent}>
              Применить
            </button>
          </div>
        </div>
      </div>
      <p className="appearance-note">Настройка личная: тема и цвет применяются только к вашему интерфейсу.</p>
    </section>
  );
}
