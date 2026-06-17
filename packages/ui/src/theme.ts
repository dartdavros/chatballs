import type { ThemeConfig } from "antd";

export const edevsHubTheme: ThemeConfig = {
  token: {
    colorPrimary: "#2563eb",
    colorSuccess: "#059669",
    colorWarning: "#d97706",
    colorError: "#dc2626",
    colorInfo: "#2563eb",
    borderRadius: 8,
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  },
  components: {
    Layout: {
      headerBg: "#ffffff",
      siderBg: "#ffffff",
      bodyBg: "#f6f8fb",
    },
    Card: {
      borderRadiusLG: 8,
    },
    Table: {
      headerBg: "#f8fafc",
    },
  },
};
