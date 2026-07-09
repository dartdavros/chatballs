import React from "react";
import ReactDOM from "react-dom/client";

import { App } from "./App";
import { SupportApp } from "./SupportApp";
import "./styles.css";

// Режим виджета выбирается URL-параметром ?mode (loader передаёт его).
// sales (default) — анонимная сессия; support — authenticated in-product чат.
const mode = new URLSearchParams(location.search).get("mode") || "sales";
const Root = mode === "support" ? SupportApp : App;

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>,
);
