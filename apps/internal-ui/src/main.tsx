import React, { lazy, Suspense, useEffect, useState } from "react";
import ReactDOM from "react-dom/client";

import { Loader } from "@chatballs/ui";

import { App } from "./App";
import { surfaceForHost, type Surface } from "./surface";
import "./styles.css";

const HelpCenterApp = lazy(() => import("./features/help-center/HelpCenterApp").then(
  (module) => ({ default: module.HelpCenterApp }),
));

function SurfaceApp() {
  const [surface, setSurface] = useState<Surface>(() => surfaceForHost(
    window.location.hostname,
    import.meta.env.VITE_APP_HOST ?? "",
  ));

  useEffect(() => {
    if (surface !== "loading") return;
    fetch("/api/v1/help/", { headers: { Accept: "application/json" } })
      .then((response) => setSurface(response.ok ? "help" : "app"))
      .catch(() => setSurface("app"));
  }, [surface]);

  useEffect(() => {
    document.documentElement.classList.toggle("help-center-document", surface === "help");
  }, [surface]);

  if (surface === "loading") {
    return <main className="help-boot-loading"><Loader size={44} /></main>;
  }
  return surface === "help"
    ? <Suspense fallback={<main className="help-boot-loading"><Loader size={44} /></main>}><HelpCenterApp /></Suspense>
    : <App />;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <SurfaceApp />
  </React.StrictMode>,
);
