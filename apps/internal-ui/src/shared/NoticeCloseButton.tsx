import type { MouseEventHandler } from "react";

import { Icon } from "./icons";

export function NoticeCloseButton({ label, onClick }: {
  label: string;
  onClick: MouseEventHandler<HTMLButtonElement>;
}) {
  return (
    <button className="notice-close" type="button" aria-label={label} onClick={onClick}>
      <Icon name="close" size={16} strokeWidth={2} />
    </button>
  );
}
