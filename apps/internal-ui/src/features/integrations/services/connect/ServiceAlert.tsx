import type { ReactNode } from "react";

import { Icon } from "../../../../shared/icons";

/** Строка-баннер окна и карточки: «<strong>Заголовок.</strong> текст» с иконкой и действием. */
export function ServiceAlert({ tone, title, text, action }: { tone: "error" | "success"; title: string; text: string; action?: ReactNode }) {
  return (
    <div className={`service-alert is-${tone}`}>
      <Icon name={tone === "error" ? "errorCircle" : "check"} size={16} strokeWidth={tone === "error" ? 1.8 : 2} />
      <p><strong>{title}</strong>{text ? ` ${text}` : ""}</p>
      {action}
    </div>
  );
}
