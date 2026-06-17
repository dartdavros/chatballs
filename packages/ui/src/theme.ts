import type { ThemeConfig } from "antd";

export const edevsHubTheme: ThemeConfig = {
  token: {
    colorPrimary: "#1677ff",
    colorSuccess: "#52c41a",
    colorWarning: "#faad14",
    colorError: "#ff4d4f",
    colorInfo: "#1677ff",
    borderRadius: 8,
    colorBgLayout: "#f0f2f5",
    colorBgContainer: "#ffffff",
    colorBorder: "#f0f0f0",
    colorText: "#262626",
    colorTextSecondary: "#8c8c8c",
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  },
  components: {
    Layout: {
      headerBg: "#ffffff",
      siderBg: "#ffffff",
      bodyBg: "#f0f2f5",
    },
    Card: {
      borderRadiusLG: 8,
    },
    Table: {
      headerBg: "#fafafa",
      headerColor: "#8c8c8c",
      rowHoverBg: "#fafbfc",
    },
    Button: {
      borderRadius: 8,
      primaryShadow: "0 1px 2px rgba(22,119,255,0.3)",
    },
  },
};
