import type { ReactNode } from 'react';
import { MessageBubble, initialsOf } from '../../../../../apps/internal-ui/src/features/conversations/MessageBubble';
import { ConversationText } from '../../../../../apps/internal-ui/src/features/conversations/ConversationText';
import { Icon } from '../../../../../apps/internal-ui/src/shared/icons';
import { agentColor, timeLabel } from './data';
import { tx } from './copy';

export function ClientMessage({ children }: { children?: ReactNode }) {
  return <MessageBubble side="client" time={timeLabel()}>{children ?? <ConversationText text={tx('question')} />}</MessageBubble>;
}
export function AiMessage({ children, text, time = timeLabel(31) }: { children?: ReactNode; text?: string; time?: string }) {
  return <MessageBubble side="ai" actor={`AI · ${tx('agentName')}`} actorColor={agentColor} time={time}>
    {children ?? <ConversationText text={text ?? tx('replyShort')} />}
  </MessageBubble>;
}
export function StaffMessage({ children, internal = false, external = false, minute = 32 }: { children: ReactNode; internal?: boolean; external?: boolean; minute?: number }) {
  const actor = internal ? tx(external ? 'externalActor' : 'systemActor') : tx('operatorName');
  return <MessageBubble side={internal && external ? 'ai' : 'operator'} internal={internal} actor={actor}
    actorColor={internal && external ? agentColor : undefined} authorInitials={internal ? 'CB' : initialsOf(tx('operatorName'))} time={timeLabel(minute)}>{children}</MessageBubble>;
}
export function Event({ children, tone = '', minute = 31 }: { children: ReactNode; tone?: 'warning' | 'claimed' | ''; minute?: number }) {
  return <div className={`sales-event-chip ${tone}`}><Icon name="clock" size={12} />{children}<span>·</span>{timeLabel(minute)}</div>;
}
// Same outgoing bubble geometry, without the normal success check for an unknown outcome.
export function UnconfirmedMessage() {
  return <div className="sales-message ai" data-delivery="unknown">
    <div className="sales-message-avatar" style={{ color: agentColor, background: `color-mix(in srgb, ${agentColor} 14%, var(--surface-card))`, borderColor: `color-mix(in srgb, ${agentColor} 30%, var(--surface-card))` }}><Icon name="robot" size={16} /></div>
    <div className="sales-message-content"><strong style={{ color: agentColor }}>{`AI · ${tx('agentName')}`}</strong>
      <div><ConversationText text={tx('replyShort')} /></div><small>{tx('notConfirmed')} · {timeLabel(31)}</small>
    </div>
  </div>;
}
