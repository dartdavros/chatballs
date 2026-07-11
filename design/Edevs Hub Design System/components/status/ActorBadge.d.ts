/**
 * @startingPoint section="Status" subtitle="AI vs human avatar for conversation timelines" viewport="700x110"
 */
export interface ActorBadgeProps {
  actor: "ai" | "human";
  /** Required when actor="human" — 1-2 letter initials. */
  initials?: string;
  color?: string;
}

export function ActorBadge(props: ActorBadgeProps): JSX.Element;
