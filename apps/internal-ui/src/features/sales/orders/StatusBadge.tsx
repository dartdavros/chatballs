import { ToneBadge } from "../../../shared/ui-controls";
import type { StatusBadge as StatusBadgeValue } from "./types";

export function StatusBadge({ value }: { value: StatusBadgeValue }) {
  return <ToneBadge className="sales-orders-status" bg={value.bg} color={value.color}>{value.label}</ToneBadge>;
}
