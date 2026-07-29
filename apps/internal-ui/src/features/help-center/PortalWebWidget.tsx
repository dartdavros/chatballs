import { useEffect } from "react";

const SCRIPT_ID = "custocrm-help-widget-loader";

export function PortalWebWidget({ channelCode }: { channelCode: string }) {
  useEffect(() => {
    if (document.getElementById(SCRIPT_ID)) return;
    const script = document.createElement("script");
    script.id = SCRIPT_ID;
    script.src = "/chat-widget.js";
    script.async = true;
    script.dataset.channel = channelCode;
    document.body.appendChild(script);
  }, [channelCode]);

  return null;
}
