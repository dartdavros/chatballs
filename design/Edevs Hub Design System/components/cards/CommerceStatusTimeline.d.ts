/**
 * @startingPoint section="Cards" subtitle="Payment vs delivery step timeline for checkout/orders" viewport="700x160"
 */
export interface CommerceStatusTimelineProps {
  steps: { label: string; state: "done" | "active" | "pending" }[];
}

export function CommerceStatusTimeline(props: CommerceStatusTimelineProps): JSX.Element;
