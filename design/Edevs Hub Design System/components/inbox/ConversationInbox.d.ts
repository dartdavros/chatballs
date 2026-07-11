export interface ConversationInboxItem {
  name: string;
  preview: string;
  channel: "max" | "telegram" | "webchat";
  lastActor: "ai" | "human";
  initials?: string;
  color?: string;
  time: string;
  waiting?: boolean;
  active?: boolean;
  onClick?: () => void;
}

/**
 * @startingPoint section="Inbox" subtitle="Realtime conversation list (channel + actor + wait state)" viewport="700x360"
 */
export interface ConversationInboxProps {
  items: ConversationInboxItem[];
}

export function ConversationInbox(props: ConversationInboxProps): JSX.Element;
