import { useEffect, useState } from "react";

export function useShopWidgetOffset(widgetKey: string | undefined) {
  const [width, setWidth] = useState(0);

  useEffect(() => {
    setWidth(0);
    if (!widgetKey) return;
    let panel: HTMLElement | null = null;
    const measure = () => setWidth(panel?.offsetWidth ?? 0);
    const sizes = new ResizeObserver(measure);
    const locate = () => {
      const next = document.querySelector<HTMLElement>(`[data-chatballs-widget-panel="${CSS.escape(widgetKey)}"]`);
      if (next === panel) return;
      sizes.disconnect();
      panel = next;
      if (panel) sizes.observe(panel);
      measure();
    };
    const panels = new MutationObserver(locate);
    panels.observe(document.body, {childList:true});
    locate();
    return () => { panels.disconnect(); sizes.disconnect(); };
  }, [widgetKey]);

  return width;
}
