import { LogoSpinner } from '../../../../../apps/internal-ui/src/shared/icons';
import { ConversationText } from '../../../../../apps/internal-ui/src/features/conversations/ConversationText';
import '../../../../../apps/internal-ui/src/features/integrations/services/services.css';
import '../../../../../apps/internal-ui/src/features/conversations/snapshot-message.css';
import { AiMessage, ClientMessage, Event, StaffMessage, UnconfirmedMessage } from './ChatMessages';
import { MultipartReply } from './MultipartReply';
import { VoiceBody } from './VoiceBody';
import type { ChatId } from './cases';
import { tx } from './copy';
import { dateLabel, timeLabel } from './data';
import { templateContent } from './template-data';
import { HelpTrigger } from '../shared/HelpTrigger';

function InternalNote({ text, external = false, minute = 32 }: { text: string; external?: boolean; minute?: number }) {
  return <div data-note-source={external ? 'external-agent' : 'chatballs'}><StaffMessage internal external={external} minute={minute}><ConversationText text={text} /></StaffMessage></div>;
}
function Waiting({ long = false }: { long?: boolean }) {
  return <div className="service-oauth-waiting" role="status" data-external-waiting>
    <span aria-hidden="true"><LogoSpinner size={18} /></span>
    <div><span className="external-help-title"><strong>{tx(long ? 'longWaiting' : 'waiting')}</strong>{long && <HelpTrigger topic="processing" />}</span><span>{tx(long ? 'longWaitingHelp' : 'waitingHelp')}</span></div>
  </div>;
}
export function ChatFeed({ variant }: { variant: ChatId }) {
  const voice = variant === 'S52' || variant === 'S53';
  return <div className="sales-timeline"><div className="sales-timeline-inner" role="log" aria-live="polite">
    <div className="sales-day-divider"><span />{dateLabel}<span /></div>
    <ClientMessage>{voice ? <VoiceBody transcribed={variant === 'S52'} /> : undefined}</ClientMessage>
    {variant === 'S40' && <Waiting />}
    {variant === 'S41' && <Waiting long />}
    {variant === 'S42' && <AiMessage text={tx('reply')} />}
    {variant === 'S43' && <MultipartReply />}
    {variant === 'S44' && <><Event tone="warning">{tx('handoffEvent')}</Event><InternalNote external text={`${tx('handoffReason')}\n\n${tx('handoffSummary')}`} /></>}
    {variant === 'S45' && <><Event tone="claimed">{tx('tookEvent')}</Event><StaffMessage><ConversationText text={tx('staffReply')} /></StaffMessage><InternalNote text={tx('suppressed')} /></>}
    {variant === 'S46' && <><Event tone="claimed">{tx('tookEvent')}</Event><StaffMessage><ConversationText text={tx('staffReply')} /></StaffMessage><Event tone="claimed" minute={33}>{tx('returnedEvent')}</Event><InternalNote text={tx('returnedHelp')} minute={33} /></>}
    {(variant === 'S47' || variant === 'S48') && <><Event tone="warning">{tx(variant === 'S47' ? 'unavailableEvent' : 'timeoutEvent')}</Event><InternalNote text={tx('queueHelp')} /></>}
    {variant === 'S49' && <><UnconfirmedMessage /><InternalNote text={`${tx('unknownTitle')}\n\n${tx('unknownHelp')}`} /></>}
    {variant === 'S50' && <><AiMessage text={tx('reply')} /><UnconfirmedMessage /><InternalNote text={`${tx('partialTitle')}\n\n${tx('partialHelp')}`} /></>}
    {variant === 'S51' && <><AiMessage text={tx('replyShort')} /><AiMessage text={tx('initiative')} time={timeLabel(40)} /><InternalNote text={tx('initiativeHelp')} minute={41} /></>}
    {variant === 'S52' && <InternalNote text={tx('voiceHelp')} />}
    {variant === 'S53' && <><Event tone="warning">{tx('voiceFailure')}</Event><InternalNote text={tx('voiceFailureHelp')} /></>}
    {variant === 'S54' && <><AiMessage><ConversationText text={templateContent().text} syntax="telegram" /></AiMessage><InternalNote text={tx('channelFallback')} /></>}
  </div></div>;
}
