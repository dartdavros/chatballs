import { useState } from "react";

import { api } from "../../api/client";
import { ACCENT_PRESETS, DEFAULT_ACCENT, type UiTheme } from "../../shared/appearance";
import { Icon } from "../../shared/icons";
import type { AuthenticatedUser, SessionUser } from "../../types";

// «Внешний вид» (дизайн-базлайн v2, кадр P1; SPEC-HUB-0031 §7): тема сегментом
// со значками, акцент — четыре пресета и произвольный HEX. Настройка личная и
// хранится в учётной записи (ADR-0029).

const THEME_OPTIONS: Array<[UiTheme, string, Parameters<typeof Icon>[0]["name"]]> = [
  ["LIGHT", "Светлая", "sunny"],
  ["DARK", "Тёмная", "moon"],
  ["SYSTEM", "Как в системе", "monitor"],
];

export function ProfileAppearanceCard({ user, onUserUpdated }: { user: SessionUser; onUserUpdated: (user: SessionUser) => void }) {
  const [saving, setSaving] = useState(false);
  const [errorText, setErrorText] = useState("");
  const accent = user.uiAccent || DEFAULT_ACCENT;
  const [customAccent, setCustomAccent] = useState(
    ACCENT_PRESETS.some(([value]) => value === accent) ? "" : accent,
  );

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
      <p className="profile-card-lead">Настройка личная и хранится в учётной записи: применяется на всех ваших устройствах, без перезагрузки.</p>
      {errorText && <div className="profile-message error">{errorText}</div>}
      <div className="appearance-row">
        <span>Тема</span>
        <div className="appearance-theme-options">
          {THEME_OPTIONS.map(([value, label, icon]) => (
            <button
              className={user.uiTheme === value ? "active" : ""}
              disabled={saving}
              key={value}
              type="button"
              onClick={() => void save(value, user.uiAccent)}
            >
              <Icon name={icon} size={13} strokeWidth={2} />
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
              style={{ background: value, "--accent-ring": value } as Record<string, string>}
              title={label}
              type="button"
              onClick={() => void save(user.uiTheme, value)}
            >
              {accent === value && <Icon name="check" size={13} strokeWidth={3} />}
            </button>
          ))}
          <i className="appearance-separator" />
          <div className="appearance-custom">
            <i className="appearance-custom-swatch" style={{ background: /^#[0-9a-f]{6}$/i.test(customAccent.trim()) ? customAccent.trim() : undefined }} />
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
            <button disabled={saving || !customAccent.trim()} type="button" onClick={submitCustomAccent}>Применить</button>
          </div>
        </div>
      </div>
    </section>
  );
}
