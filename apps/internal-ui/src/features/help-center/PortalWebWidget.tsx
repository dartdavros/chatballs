import { useEffect } from "react";

const SCRIPT_ID = "chatballs-help-widget-loader";

export function PortalWebWidget({ widgetKey }: { widgetKey: string }) {
  useEffect(() => {
    if (document.getElementById(SCRIPT_ID)) return;
    const script = document.createElement("script");
    script.id = SCRIPT_ID;
    script.src = "/chat-widget.js";
    script.async = true;
    script.dataset.widgetKey = widgetKey;
    document.body.appendChild(script);
  }, [widgetKey]);

  return null;
}
