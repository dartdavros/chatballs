import React from "react";
import ReactDOM from "react-dom/client";

import { CallApp } from "./CallApp";
import "../styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <CallApp />
  </React.StrictMode>,
);
