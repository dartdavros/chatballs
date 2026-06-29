import { useState } from "react";

import { Icon } from "../../../shared/icons";

const actions = [
  { label: "Запустить сверку", icon: "refresh" as const },
  { label: "Открыть в продукте", icon: "external" as const },
  { label: "Исправить атрибуцию", icon: "edit" as const },
  { label: "Операционный комментарий", icon: "message" as const },
];

export function OrderDetailActions() {
  const [open, setOpen] = useState(false);

  return (
    <div className="order-detail-actions">
      {open && <button className="order-detail-menu-backdrop" type="button" aria-label="Закрыть меню действий" onClick={() => setOpen(false)} />}
      <button className={`order-detail-action-trigger ${open ? "active" : ""}`} type="button" onClick={() => setOpen((value) => !value)}>
        Действия
        <Icon name="chevron" size={14} />
      </button>
      {open && (
        <div className="order-detail-menu">
          {actions.map((action) => (
            <button type="button" key={action.label}>
              <Icon name={action.icon} size={15} />
              {action.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
