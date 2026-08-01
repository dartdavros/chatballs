import { ChatHeader } from "./ChatView";

export const SUPPORT_ACCENT = "#1677ff";

function closePanel() {
  window.parent.postMessage({ type: "edevs-chat-close" }, "*");
}

export function supportShell(): React.CSSProperties {
  return {
    display: "flex",
    flexDirection: "column",
    height: "100%",
    width: "100%",
    background: "#fff",
    fontFamily: "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif",
    color: "#1f1f1f",
    overflow: "hidden",
  };
}

export function SupportStatusScreen({ failed }: { failed: boolean }) {
  const statusLabel = failed ? "Временно недоступна" : "Подключение…";
  const statusDot = failed ? "#faad14" : "#52c41a";
  return (
    <div style={supportShell()}>
      <ChatHeader
        accent={SUPPORT_ACCENT}
        letter="П"
        title="Поддержка"
        statusLabel={statusLabel}
        statusDot={statusDot}
        unavailable={false}
        onClose={closePanel}
      />
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", background: "#f7f8fa" }}>
        {failed
          ? <p style={{ color: "#595959", fontSize: 13, padding: 24, textAlign: "center" }}>Поддержка временно недоступна. Обновите страницу или обратитесь позже.</p>
          : <span style={{ color: "#8c8c8c", fontSize: 13 }}>Загрузка…</span>}
      </div>
    </div>
  );
}
