import { ApartmentOutlined, RobotOutlined, ShoppingOutlined, TeamOutlined } from "@ant-design/icons";
import { ConfigProvider, Layout, Menu, Tag, Typography } from "antd";
import { edevsHubTheme } from "@edevs/ui";

const { Header, Sider, Content } = Layout;

export function App() {
  return (
    <ConfigProvider theme={edevsHubTheme}>
      <Layout className="hub-shell">
        <Sider width={256} className="hub-sidebar">
          <div className="hub-logo">Edevs Hub</div>
          <Menu
            mode="inline"
            selectedKeys={["command-center"]}
            items={[
              { key: "command-center", icon: <ApartmentOutlined />, label: "Командный центр" },
              { type: "group", label: "Компания" },
              { key: "departments", icon: <TeamOutlined />, label: "Отделы" },
              { key: "products", icon: <ShoppingOutlined />, label: "Продукты" },
              { type: "group", label: "Платформа" },
              { key: "ai", icon: <RobotOutlined />, label: "AI" },
            ]}
          />
        </Sider>
        <Layout>
          <Header className="hub-header">
            <Typography.Text type="secondary">Edevs / Командный центр</Typography.Text>
            <Tag color="success">Локальный контур</Tag>
          </Header>
          <Content className="hub-content">
            <section className="page-header">
              <Typography.Title level={1}>Командный центр</Typography.Title>
              <Typography.Text type="secondary">
                Первый рабочий каркас внутреннего Hub. Реальные домены подключаются на следующих этапах.
              </Typography.Text>
            </section>
            <section className="department-grid">
              <article className="department-card">
                <div>
                  <Typography.Title level={2}>Продажи</Typography.Title>
                  <Tag color="default">NORMAL</Tag>
                </div>
                <p>Данные отдела появятся после реализации доменных модулей продаж, коммуникаций и коммерческого ядра.</p>
              </article>
            </section>
          </Content>
        </Layout>
      </Layout>
    </ConfigProvider>
  );
}
