import type { ReactNode } from "react";

import { Icon } from "../../../shared/icons";
import type { TestChannel } from "./model";

const channelLabel: Record<TestChannel, string> = {
  MAX: "MAX",
  TG: "Telegram",
  WEB: "Web Chat",
};

export function TestConversation({ channel }: { channel: TestChannel }) {
  return (
    <section className="test-conversation">
      <div className="test-conversation-head">
        <div className="test-conversation-title">
          <span><Icon name="robot" size={18} /></span>
          <div>
            <strong>Test conversation</strong>
            <small>Симуляция клиента · сообщений: 4</small>
          </div>
        </div>
        <em><Icon name="eyeOff" size={13} />Не создаёт Contact, Order или Payment</em>
      </div>

      <div className="test-messages">
        <div className="test-scenario-pill">Сценарий: «Покупка коробки» · канал {channelLabel[channel]}</div>
        <ClientMessage text="Здравствуйте, интересует FirePage для сайта-визитки. Сколько стоит?" note="тестовый клиент" />
        <AiMessage>
          Здравствуйте! FirePage — это готовый нишевой сайт под ключ. Коробка стоит <b>₽4 900</b> единоразово. Дополнительно можно подключить годовую поддержку за ₽1 470. Под визитку отлично подходит — оформить?
        </AiMessage>
        <ClientMessage text="Да, давайте оформим коробку." />
        <AiMessage tool="create_checkout">
          Отлично! Подготовил оформление коробки FirePage за ₽4 900. Вызываю оформление покупки — в реальном диалоге клиент получил бы ссылку на оплату.
        </AiMessage>
      </div>

      <div className="test-composer">
        <div>
          <textarea rows={1} placeholder="Сообщение от лица тестового клиента…" />
          <button type="button">Отправить<Icon name="send" size={15} /></button>
        </div>
      </div>
    </section>
  );
}

function ClientMessage({ note, text }: { note?: string; text: string }) {
  return (
    <div className="test-message client">
      <span className="test-client-avatar">Т</span>
      <div>
        <p>{text}</p>
        {note && <small>{note}</small>}
      </div>
    </div>
  );
}

function AiMessage({ children, tool }: { children: ReactNode; tool?: string }) {
  return (
    <div className="test-message ai">
      <span className="test-ai-avatar"><Icon name="robot" size={16} /></span>
      <div>
        <strong>AI · REL-FP-v5</strong>
        <p>{children}</p>
        {tool && <em>tool: {tool}</em>}
      </div>
    </div>
  );
}
