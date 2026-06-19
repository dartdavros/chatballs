import { Icon } from "../../../shared/icons";
import { ToneBadge } from "../../../shared/ui-controls";

export function OrderSuccessBadge({ children, className = "" }: { children: string; className?: string }) {
  return (
    <ToneBadge className={`order-success-badge ${className}`.trim()} bg="#f6ffed" color="#389e0d">
      <Icon name="check" size={13} />
      {children}
    </ToneBadge>
  );
}
