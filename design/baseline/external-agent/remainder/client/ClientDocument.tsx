import { useRef, type MouseEvent } from 'react';
import { ChatBody } from '../../../../../apps/web-chat/src/ChatBody';
import { ChatHeader } from '../../../../../apps/web-chat/src/ChatHeader';
import { ChatComposer } from '../../../../../apps/web-chat/src/ChatComposer';
import { StartChatFooter } from '../../../../../apps/web-chat/src/StartChatFooter';
import { PreChatForm } from '../../../../../apps/web-chat/src/PreChatForm';
import { BrandFooter } from '../../../../../apps/web-chat/src/BrandFooter';
import { WidgetStyles } from '../../../../../apps/web-chat/src/WidgetStyles';
import { widgetClasses as classes } from '../../../../../apps/web-chat/src/widgetClasses';
import { ClientVoiceBody } from './ClientVoiceBody';
import { clientText } from './copy';
import { consentConfig, emptyAttachment, idleVoice, noop, widgetAccent } from './model';
import type { ClientVariant } from './cases';

function keepDocumentStatic(event: MouseEvent) {
  if ((event.target as Element).closest('button, a')) {
    event.preventDefault(); event.stopPropagation();
  }
}

export function ClientDocument({ variant, mobile }: { variant: ClientVariant; mobile: boolean }) {
  const bodyRef = useRef<HTMLDivElement>(null);
  const form = variant === 'S61';
  const accepted = variant === 'S62' || variant === 'S63';
  const config = consentConfig(form);
  return <div className={classes.root} data-consent-state={accepted ? 'current-illustration' : 'required'}
    onClickCapture={keepDocumentStatic} onSubmitCapture={event => event.preventDefault()}
    style={{ '--cb-accent': widgetAccent } as React.CSSProperties}>
    <WidgetStyles customCss="" />
    <ChatHeader accent={widgetAccent} title={clientText('title')} expanded={false} canExpand={!mobile}
      onToggleExpand={noop} onClose={noop} />
    {form ? <PreChatForm config={config} accent={widgetAccent} title={clientText('title')} siteValues={{}}
      starting={false} onAccept={async () => {}} />
      : variant === 'S63' ? <ClientVoiceBody />
        : <ChatBody bodyRef={bodyRef} config={config} unavailable={false} accepted={accepted}
          accent={widgetAccent} title={clientText('title')} messages={[]} pending={[]} awaiting={false}
          lastContactRequestId={0} showPhoneForm={false} onSubmitContact={async () => false} />}
    {!accepted && !form && <StartChatFooter accent={widgetAccent} starting={false} onAccept={noop} />}
    {accepted && <ChatComposer accent={widgetAccent} input="" onInput={noop} onSend={noop}
      voice={idleVoice} attachment={emptyAttachment} />}
    <BrandFooter accent={widgetAccent} />
  </div>;
}
