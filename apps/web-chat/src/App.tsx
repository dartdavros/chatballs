import { ConfigProvider, FloatButton, Typography } from "antd";
import { edevsHubTheme } from "@edevs/ui";

export function App() {
  return (
    <ConfigProvider theme={edevsHubTheme}>
      <main className="web-chat-demo">
        <section className="chat-panel">
          <Typography.Title level={2}>Web Chat</Typography.Title>
          <Typography.Paragraph>
            Каркас публичного виджета готов. Детальная реализация UI ждёт прохождения DG-04.
          </Typography.Paragraph>
        </section>
        <FloatButton badge={{ dot: true }} tooltip="Открыть чат" />
      </main>
    </ConfigProvider>
  );
}
