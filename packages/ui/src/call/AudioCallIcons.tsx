// Иконки аудиозвонка (baseline «Аудиозвонок.dc.html»): stroke=currentColor,
// 1.85, round caps. Микрофон/динамик (аудио не имеет камеры), завершение и
// status-набор для процессов/ошибок/терминалов.

import type { ReactNode } from "react";

export type DeviceName = "mic" | "speaker";

const svg =
  (width = 23) =>
  (children: ReactNode) =>
    (
      <svg viewBox="0 0 24 24" width={width} height={width} fill="none" stroke="currentColor" strokeWidth={1.85} strokeLinecap="round" strokeLinejoin="round">
        {children}
      </svg>
    );

export function MicIcon({ on }: { on: boolean }) {
  const s = svg(23);
  return on
    ? s(<><rect x="9" y="2" width="6" height="12" rx="3" /><path d="M19 10v1a7 7 0 0 1-14 0v-1" /><line x1="12" y1="18" x2="12" y2="22" /></>)
    : s(<><line x1="3" y1="3" x2="21" y2="21" /><path d="M9 9v2a3 3 0 0 0 5.1 2.1" /><path d="M15 9.3V5a3 3 0 0 0-5.9-.7" /><path d="M19 10v1a7 7 0 0 1-1.4 4.2M12 18a7 7 0 0 1-7-7v-1" /><line x1="12" y1="18" x2="12" y2="22" /></>);
}

export function SpeakerIcon({ on }: { on: boolean }) {
  const s = svg(23);
  return on
    ? s(<><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" /><path d="M15.5 8.5a5 5 0 0 1 0 7" /><path d="M19 5a9 9 0 0 1 0 14" /></>)
    : s(<><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" /><line x1="22" y1="9" x2="16" y2="15" /><line x1="16" y1="9" x2="22" y2="15" /></>);
}

// Трубка; rotated=true → повёрнута на 135° (отклонить/завершить/отменить).
export function PhoneIcon({ rotated = false, width = 26 }: { rotated?: boolean; width?: number }) {
  const s = svg(width);
  return s(
    <path
      style={rotated ? { transform: "rotate(135deg)", transformOrigin: "center" } : undefined}
      d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.81.36 1.6.7 2.34a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.74-1.27a2 2 0 0 1 2.11-.45c.74.34 1.53.57 2.34.7A2 2 0 0 1 22 16.92z"
    />
  );
}

export function SpinnerIcon({ width = 34 }: { width?: number }) {
  const s = svg(width);
  return s(<path style={{ animation: "hub-audio-spin .9s linear infinite" }} d="M21 12a9 9 0 1 1-6.219-8.56" strokeWidth={2} />);
}

export type AudioStatusIconName = "spinner" | "declined" | "missed" | "clock" | "alert" | "nodevice" | "unsupported";

export function AudioStatusIcon({ name }: { name: AudioStatusIconName }) {
  const s = svg(34);
  switch (name) {
    case "spinner":
      return <SpinnerIcon />;
    case "declined":
      return s(<path transform="rotate(135 12 12)" d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.81.36 1.6.7 2.34a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.74-1.27a2 2 0 0 1 2.11-.45c.74.34 1.53.57 2.34.7A2 2 0 0 1 22 16.92z" />);
    case "missed":
      return s(<><path d="M23 7l-8 8-4-4-9 9" /><polyline points="17 7 23 7 23 13" /></>);
    case "clock":
      return s(<><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>);
    case "alert":
      return s(<><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></>);
    case "nodevice":
      return s(<><line x1="2" y1="2" x2="22" y2="22" /><path d="M16 16v1a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h2" /><path d="M10 5h4a2 2 0 0 1 2 2v3l4-3v9" /></>);
    case "unsupported":
      return s(<><rect x="2" y="3" width="20" height="14" rx="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" /><line x1="9" y1="8" x2="15" y2="14" /><line x1="15" y1="8" x2="9" y2="14" /></>);
    default:
      return null;
  }
}
