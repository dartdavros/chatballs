import { theme as antdTheme } from "antd";
import type { ThemeConfig } from "antd";

// Персональная тема и акцент (SPEC-CHATBALLS-0031 §7): antd-конфиг собирается из
// выбранных пользователем режима (light/dark) и акцентного цвета.
export function buildTheme(dark: boolean, accent: string): ThemeConfig {
  const base = chatballsTheme;
  if (!dark) {
    return {
      ...base,
      token: { ...base.token, colorPrimary: accent, colorInfo: accent },
    };
  }
  return {
    algorithm: antdTheme.darkAlgorithm,
    token: {
      ...base.token,
      colorPrimary: accent,
      colorInfo: accent,
      // Нейтрали тёмной темы — из дизайн-базлайна v2.
      colorBgLayout: "#101113",
      colorBgContainer: "#1b1c1f",
      colorBorder: "#2d2f35",
      colorText: "#c3c5ca",
      colorTextSecondary: "#767881",
    },
    components: {
      ...base.components,
      Layout: { headerBg: "#1b1c1f", siderBg: "#181a1d", bodyBg: "#101113" },
      Table: { headerBg: "#212327", headerColor: "#767881", rowHoverBg: "#212327" },
      Button: base.components?.Button,
    },
  };
}

export const chatballsTheme: ThemeConfig = {
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
