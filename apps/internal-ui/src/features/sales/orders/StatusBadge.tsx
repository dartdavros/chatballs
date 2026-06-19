import type { AnchorHTMLAttributes } from "react";

import { MonoLink as SharedMonoLink, ToneBadge } from "../../../shared/ui-controls";
import type { StatusBadge as StatusBadgeValue } from "./types";

export function StatusBadge({ value }: { value: StatusBadgeValue }) {
  return <ToneBadge className="sales-orders-status" bg={value.bg} color={value.color}>{value.label}</ToneBadge>;
}

export function MonoLink({ children, ...linkProps }: AnchorHTMLAttributes<HTMLAnchorElement> & { children: string }) {
  return <SharedMonoLink className="sales-orders-mono-link" {...linkProps}>{children}</SharedMonoLink>;
}
