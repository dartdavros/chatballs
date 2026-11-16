import type { MouseEvent } from 'react';
import { ChatSidebar } from './ChatSidebar';
import { ChatList } from './ChatList';
import { ChatHead } from './ChatHead';
import { ChatContext } from './ChatContext';
import { ChatFeed } from './ChatFeed';
import { ChatComposer } from './ChatComposer';
import { chatIds, type ChatId } from './cases';
import './chat.css';
export { chatCases } from './cases';

function staticAction(event: MouseEvent<HTMLDivElement>) {
  if ((event.target as Element).closest('[data-help-topic], .external-help-modal')) return;
  if ((event.target as Element).closest('a, button')) { event.preventDefault(); event.stopPropagation(); }
}
export function ChatSuite({ variant, width, height }: { variant: string; width: number; height: number }) {
  const id: ChatId = chatIds.includes(variant as ChatId) ? variant as ChatId : 'S40';
  return <div className="ea-screen" data-screen={id} data-staff-chat style={{ width, height }} onClickCapture={staticAction}>
    <div className="hub-shell is-chat-route" style={{ height: '100%' }}>
      <ChatSidebar variant={id} />
      <div className="hub-main"><main className="hub-scroll sales-dialogs-scroll"><div className="hub-page sales-dialogs-page">
        <div className={`sales-dialogs${width <= 768 ? ' is-mobile-dialog' : ''}`}>
          <ChatList variant={id} />
          <section className="sales-conversation"><ChatHead variant={id} /><ChatFeed variant={id} /><ChatComposer variant={id} compact={width <= 768} /></section>
          <ChatContext variant={id} />
        </div>
      </div></main></div>
    </div>
  </div>;
}
