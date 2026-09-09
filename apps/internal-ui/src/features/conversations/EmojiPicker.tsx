import { Dropdown } from "antd";
import { useState } from "react";

import { Icon } from "../../shared/icons";
import { t } from "../../i18n";

// Эмодзи в композере (дизайн-базлайн v2, кнопка «Эмодзи»): antd Dropdown —
// единый стандарт всплывающих меню — с сеткой частых эмодзи для переписки.

const EMOJI = [
  "😀", "😊", "😉", "😂", "🙂", "😍", "🤔", "😅", "🙏", "👍", "👌", "🤝",
  "👋", "✅", "❌", "⭐", "🔥", "🎉", "❤️", "💙", "💚", "✨", "📦", "🚚",
  "📞", "📧", "📎", "📅", "⏰", "💬", "🧵", "✂️", "📏", "🪡", "🛒", "💳",
];

export function EmojiPicker({ onPick, disabled }: { onPick: (emoji: string) => void; disabled?: boolean }) {
  const [open, setOpen] = useState(false);
  return (
    <Dropdown
      open={open}
      onOpenChange={setOpen}
      trigger={["click"]}
      placement="topLeft"
      overlayClassName="app-dropdown composer-emoji"
      disabled={disabled}
      popupRender={() => (
        <div className="ant-dropdown-menu composer-emoji-grid" role="listbox" aria-label={t("common.emoji")}>
          {EMOJI.map((emoji) => (
            <button
              key={emoji}
              type="button"
              role="option"
              aria-selected={false}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => { onPick(emoji); setOpen(false); }}
            >
              {emoji}
            </button>
          ))}
        </div>
      )}
    >
      <button className="composer-tool" title={t("common.emoji")} aria-label={t("common.emoji")} type="button" disabled={disabled}>
        <Icon name="smile" size={17} />
      </button>
    </Dropdown>
  );
}
