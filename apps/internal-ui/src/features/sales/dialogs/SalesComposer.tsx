import { Icon } from "../../../shared/icons";
import type { ControlMode } from "./types";

export function SalesComposer({ mode, setMode }: { mode: ControlMode; setMode: (mode: ControlMode) => void }) {
  if (mode === "waiting") {
    return (
      <div className="sales-composer"><div className="sales-waiting-composer">
        <span><Icon name="lock" size={19} /></span>
        <div><strong>Диалог ждёт оператора</strong><p>Возьмите диалог, чтобы ответить клиенту. AI поставлен на паузу.</p></div>
        <button className="sales-secondary-action">Вернуть в очередь</button>
        <button className="sales-claim-button" onClick={() => setMode("human")}><Icon name="check" size={15} />Забрать диалог</button>
      </div></div>
    );
  }

  if (mode === "ai") {
    return (
      <div className="sales-composer"><div className="sales-ai-composer">
        <span><Icon name="robot" size={19} /></span>
        <div><strong>AI ведёт диалог</strong><p>Перехватите, чтобы ответить вручную. Контроль перейдёт к вам.</p></div>
        <button className="sales-ai-button" onClick={() => setMode("human")}>Перехватить AI</button>
      </div></div>
    );
  }

  return (
    <div className="sales-composer">
      <div className="sales-human-tools">
        <button>Шаблоны ответов</button>
        <button>Создать ссылку покупки</button>
        <span />
        <button className="ai" onClick={() => setMode("ai")}>Вернуть AI</button>
        <button>Закрыть</button>
      </div>
      <div className="sales-message-input">
        <button aria-label="Прикрепить файл"><Icon name="paperclip" size={19} /></button>
        <textarea rows={1} placeholder="Введите сообщение…" />
        <button>Отправить<Icon name="send" size={15} /></button>
      </div>
    </div>
  );
}
