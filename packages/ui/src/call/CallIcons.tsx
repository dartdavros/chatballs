import { Loader } from "../loader/Loader";

type IconProps = { kind: "mic" | "cam"; on?: boolean };

const common = {
  viewBox: "0 0 24 24",
  width: 22,
  height: 22,
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.85,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export function DeviceIcon({ kind, on = true }: IconProps) {
  if (kind === "mic") {
    return on ? (
      <svg {...common}><rect x="9" y="2" width="6" height="12" rx="3" /><path d="M19 10v1a7 7 0 0 1-14 0v-1" /><line x1="12" y1="18" x2="12" y2="22" /></svg>
    ) : (
      <svg {...common}><line x1="3" y1="3" x2="21" y2="21" /><path d="M9 9v2a3 3 0 0 0 5.1 2.1" /><path d="M15 9.3V5a3 3 0 0 0-5.9-.7" /><path d="M19 10v1a7 7 0 0 1-1.4 4.2M12 18a7 7 0 0 1-7-7v-1" /><line x1="12" y1="18" x2="12" y2="22" /></svg>
    );
  }
  return on ? (
    <svg {...common}><path d="M23 7l-7 5 7 5V7z" /><rect x="1" y="5" width="15" height="14" rx="2.5" /></svg>
  ) : (
    <svg {...common}><line x1="2" y1="2" x2="22" y2="22" /><path d="M16 16v1a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h2" /><path d="M10 5h4a2 2 0 0 1 2 2v3l4-3v9" /></svg>
  );
}

export function PhoneIcon() {
  return <svg {...common} width="24" height="24" style={{ transform: "rotate(135deg)" }}><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.81.36 1.6.7 2.34a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.74-1.27a2 2 0 0 1 2.11-.45c.74.34 1.53.57 2.34.7A2 2 0 0 1 22 16.92z" /></svg>;
}

export function CloseIcon() {
  return <svg {...common} width="17" height="17"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>;
}

export function FullscreenIcon() {
  return <svg {...common} width="21" height="21"><path d="M8 3H5a2 2 0 0 0-2 2v3" /><path d="M21 8V5a2 2 0 0 0-2-2h-3" /><path d="M3 16v3a2 2 0 0 0 2 2h3" /><path d="M16 21h3a2 2 0 0 0 2-2v-3" /></svg>;
}

export function SpinnerIcon() {
  return <Loader size={16} />;
}

export type StatusIconName = "spinner" | "alert" | "declined" | "missed" | "clock" | "unsupported";

export function StatusIcon({ name }: { name: StatusIconName }) {
  if (name === "spinner") return <Loader size={26} />;
  if (name === "alert") return <svg {...common} width="26" height="26"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>;
  if (name === "declined") return <svg {...common} width="26" height="26"><path transform="rotate(135 12 12)" d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.81.36 1.6.7 2.34a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.74-1.27a2 2 0 0 1 2.11-.45c.74.34 1.53.57 2.34.7A2 2 0 0 1 22 16.92z" /></svg>;
  if (name === "missed") return <svg {...common} width="26" height="26"><path d="M23 7l-8 8-4-4-9 9" /><polyline points="17 7 23 7 23 13" /></svg>;
  if (name === "unsupported") return <svg {...common} width="26" height="26"><circle cx="12" cy="12" r="9" /><line x1="8" y1="8" x2="16" y2="16" /></svg>;
  return <svg {...common} width="26" height="26"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>;
}
