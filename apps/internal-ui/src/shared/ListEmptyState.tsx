import type { ReactNode } from "react";

import { Icon } from "./icons";
import "./list-empty-state.css";

export function ListEmptyState({ icon, title, text, action }: {
  icon: Parameters<typeof Icon>[0]["name"];
  title: string;
  text: string;
  action: ReactNode;
}) {
  return (
    <div className="list-empty-state">
      <span className="list-empty-state-icon" aria-hidden="true"><Icon name={icon} size={24} /></span>
      <div>
        <strong>{title}</strong>
        <p>{text}</p>
      </div>
      {action}
    </div>
  );
}
