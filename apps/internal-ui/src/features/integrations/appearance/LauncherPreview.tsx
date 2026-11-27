import { useLayoutEffect, useRef, useState, type CSSProperties } from "react";
import { createPortal } from "react-dom";
import { SHAPE_RADIUS, type WidgetAppearance } from "./model";
import { WidgetIcon } from "./WidgetIcon";

const BUTTON_CSS = `
  .cb-launcher {
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: center;
    width: var(--preview-size);
    height: var(--preview-size);
    border-radius: var(--preview-radius);
    background: var(--widget-accent);
    color: #fff;
    box-shadow: 0 6px 18px rgb(0 0 0 / 22%);
  }
`;

export function LauncherPreview({ appearance, css, onHeight }: {
  appearance: WidgetAppearance;
  css: string;
  onHeight: (height: number) => void;
}) {
  const host = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLDivElement>(null);
  const [shadow, setShadow] = useState<ShadowRoot | null>(null);
  const isolated = Boolean(css);
  useLayoutEffect(() => {
    if (!isolated || !host.current) return;
    setShadow(host.current.shadowRoot ?? host.current.attachShadow({ mode: "open" }));
  }, [isolated]);
  useLayoutEffect(() => {
    if (!isolated || !button.current) return;
    const element = button.current;
    const measure = () => onHeight(element.offsetHeight);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [isolated, shadow, onHeight]);
  const side = { [appearance.launcherPosition]: 16 };
  const radius = SHAPE_RADIUS[appearance.launcherShape];
  const icon = <WidgetIcon url={appearance.launcherIcon} size={Math.round(appearance.launcherSize * 0.55)} />;
  if (!isolated) {
    return <div className="widget-preview-launcher" style={{ ...side, width: appearance.launcherSize, height: appearance.launcherSize, borderRadius: radius }}>{icon}</div>;
  }
  return <div ref={host} style={{ position: "absolute", bottom: 16, ...side,
    "--preview-size": `${appearance.launcherSize}px`, "--preview-radius": radius } as CSSProperties}>
    {shadow && createPortal(<><style>{BUTTON_CSS + css}</style>
      <div className="cb-launcher chatballs-chat-launcher" ref={button}>{icon}</div>
    </>, shadow)}
  </div>;
}
