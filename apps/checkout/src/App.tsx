import { ConfigProvider, Result } from "antd";
import { edevsHubTheme } from "@edevs/ui";

export function App() {
  return (
    <ConfigProvider theme={edevsHubTheme}>
      <main className="checkout-shell">
        <Result
          status="info"
          title="Оформление покупки"
          subTitle="Публичный checkout будет реализован после прохождения DG-05. Каркас приложения готов для E01."
        />
      </main>
    </ConfigProvider>
  );
}
