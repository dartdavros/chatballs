import type { ReactNode } from "react";

import { Loader } from "@chatballs/ui";

// Логотип Chatballs (файл владельца, 2026-09-05): два круга и перемычка, вырезы
// сверху и снизу. Цвет — currentColor: белый на акценте, тёмный на светлом фоне.
export function LogoIcon({ size = 17 }: { size?: number }) {
  return (
    <svg viewBox="0 0 100 100" width={size} height={size} fill="currentColor" aria-hidden="true">
      <defs>
        <mask id="chatballs-logo-mask">
          <rect width="100" height="100" fill="white" />
          <circle cx="50" cy="24.54" r="9" fill="black" />
          <circle cx="50" cy="75.46" r="9" fill="black" />
        </mask>
      </defs>
      <g mask="url(#chatballs-logo-mask)">
        <circle cx="29" cy="50" r="24" />
        <circle cx="71" cy="50" r="24" />
        <rect x="44.2" y="31.4" width="11.6" height="37.2" />
      </g>
    </svg>
  );
}

// Загрузчик продукта: общий морф-прелоадер из @chatballs/ui. Имя LogoSpinner
// и класс logo-spinner сохранены — на них завязаны стили размещения. Цвет —
// currentColor, то есть цвет своей темы задаёт контейнер.
export function LogoSpinner({ size = 28, className = "" }: { size?: number; className?: string }) {
  return <Loader size={size} className={`logo-spinner ${className}`.trim()} />;
}

export function ShieldIcon() {
  return (
    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
      <path d="m9 12 2 2 4-5" />
    </svg>
  );
}

// Фирменные марки каналов (SPEC-CHATBALLS-0025 §2.3): официальные SVG-глифы, залитые
// currentColor — цвет задаёт плитка подключения. Не перерисовывать.
export function TelegramLogo({ size = 24 }: { size?: number }) {
  return (
    <svg viewBox="0 0 512 512" width={size} height={size} fill="currentColor">
      <path d="M512 256C512 114.62 397.38 0 256 0S0 114.62 0 256s114.62 256 256 256 256-114.62 256-256zm-396.12-2.7c74.63-32.52 124.39-53.95 149.29-64.31 71.1-29.57 85.87-34.71 95.5-34.88 2.12-.03 6.85.49 9.92 2.98 2.59 2.1 3.3 4.94 3.64 6.93.34 2 .77 6.53.43 10.08-3.85 40.48-20.52 138.71-29 184.05-3.59 19.19-10.66 25.62-17.5 26.25-14.86 1.37-26.15-9.83-40.55-19.27-22.53-14.76-35.26-23.96-57.13-38.37-25.28-16.66-8.89-25.81 5.51-40.77 3.77-3.92 69.27-63.5 70.54-68.9.16-.68.31-3.2-1.19-4.53s-3.71-.87-5.3-.51c-2.26.51-38.25 24.3-107.98 71.37-10.22 7.02-19.48 10.43-27.77 10.26-9.14-.2-26.72-5.17-39.79-9.42-16.03-5.21-28.77-7.97-27.66-16.82.57-4.61 6.92-9.32 19.04-14.14z" />
    </svg>
  );
}

export function MaxLogo({ size = 24 }: { size?: number }) {
  return (
    <svg viewBox="0 0 720 720" width={size} height={size} fill="currentColor">
      <path d="M350.4,9.6C141.8,20.5,4.1,184.1,12.8,390.4c3.8,90.3,40.1,168,48.7,253.7,2.2,22.2-4.2,49.6,21.4,59.3,31.5,11.9,79.8-8.1,106.2-26.4,9-6.1,17.6-13.2,24.2-22,27.3,18.1,53.2,35.6,85.7,43.4,143.1,34.3,299.9-44.2,369.6-170.3C799.6,291.2,622.5-4.6,350.4,9.6h0ZM269.4,504c-11.3,8.8-22.2,20.8-34.7,27.7-18.1,9.7-23.7-.4-30.5-16.4-21.4-50.9-24-137.6-11.5-190.9,16.8-72.5,72.9-136.3,150-143.1,78-6.9,150.4,32.7,183.1,104.2,72.4,159.1-112.9,316.2-256.4,218.6h0Z" />
    </svg>
  );
}

export function Icon({ name, size = 17, strokeWidth = 1.8 }: { name: "grid" | "building" | "team" | "box" | "robot" | "plug" | "settings" | "bell" | "chevron" | "chevronLeft" | "chevronRight" | "plus" | "arrow" | "paperclip" | "send" | "phone" | "video" | "lock" | "mail" | "eye" | "eyeOff" | "logout" | "user" | "refresh" | "transfer" | "warning" | "alert" | "bolt" | "shop" | "search" | "more" | "external" | "key" | "pause" | "play" | "percent" | "save" | "check" | "copy" | "clock" | "message" | "inbox" | "cart" | "columns" | "download" | "list" | "split" | "gitBranch" | "route" | "expand" | "edit" | "trash" | "wrench" | "xCircle" | "close" | "folder" | "grip" | "reply" | "sort" | "collapseLeft" | "mic" | "text" | "pin" | "smile" | "globe" | "doc" | "sparkles" | "database" | "sun" | "sunny" | "moon" | "monitor" | "laptop" | "smartphone" | "arrowDown" | "link" | "paint" | "widget" | "danger" | "image" | "file" | "bold" | "italic" | "code" | "numlist" | "quote" | "table" | "attach" | "undo" | "upload" | "import" | "thumbUp" | "thumbDown" | "book" | "move"; size?: number; strokeWidth?: number }) {
  const common = { width: size, height: size, fill: "none", stroke: "currentColor", strokeWidth, strokeLinecap: "round", strokeLinejoin: "round" } as const;
  const paths: Record<typeof name, ReactNode> = {
    thumbUp: <><path d="M7 10v11H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3z" /><path d="M7 10 11 3a2.2 2.2 0 0 1 4 1.8L14.5 8H20a2 2 0 0 1 2 2.4l-1.4 7A4 4 0 0 1 16.7 21H7" /></>,
    thumbDown: <g transform="rotate(180 12 12)"><path d="M7 10v11H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3z" /><path d="M7 10 11 3a2.2 2.2 0 0 1 4 1.8L14.5 8H20a2 2 0 0 1 2 2.4l-1.4 7A4 4 0 0 1 16.7 21H7" /></g>,
    grid: <><rect x="3" y="3" width="7" height="9" rx="1.4" /><rect x="14" y="3" width="7" height="5" rx="1.4" /><rect x="14" y="12" width="7" height="9" rx="1.4" /><rect x="3" y="16" width="7" height="5" rx="1.4" /></>,
    building: <path d="M3 21h18M5 21V7l7-4 7 4v14M9 21v-6h6v6M9 10h.01M15 10h.01" />,
    team: <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0zM23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />,
    inbox: <><polyline points="22 12 16 12 14 15 10 15 8 12 2 12" /><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" /></>,
    box: <path d="M21 8 12 3 3 8v8l9 5 9-5zM3 8l9 5 9-5M12 13v8" />,
    // Tabler ti-robot. Глаза — точки: рисуются нулевыми сегментами v.01
    // и держатся на strokeLinecap="round" из common.
    robot: <path d="M6 6a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2zM12 2v2M9 12v9M15 12v9M9 18h6M10 8v.01M14 8v.01" />,
    // Tabler ti-plug.
    plug: <path d="M12 22v-5M9 8V2M15 8V2M18 8v5a6 6 0 0 1-12 0V8z" />,
    settings: <><line x1="21" y1="6" x2="9" y2="6" /><line x1="3" y1="6" x2="5" y2="6" /><circle cx="7" cy="6" r="2" /><line x1="21" y1="12" x2="13" y2="12" /><line x1="3" y1="12" x2="9" y2="12" /><circle cx="11" cy="12" r="2" /><line x1="21" y1="18" x2="15" y2="18" /><line x1="3" y1="18" x2="11" y2="18" /><circle cx="13" cy="18" r="2" /></>,
    bell: <><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" /><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" /></>,
    message: <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2Z" />,
    cart: <><path d="M2 3h2l2.6 12.4a2 2 0 0 0 2 1.6h9.7a2 2 0 0 0 2-1.6L23 6H6" /><circle cx="9" cy="20" r="1" /><circle cx="18" cy="20" r="1" /></>,
    globe: <path d="M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM2 12h20M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />,
    // Документ библиотеки знаний (строка блока «Знания» на карточке агента).
    doc: <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M8 13h8M8 17h5" />,
    columns: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /></>,
    download: <><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></>,
    list: <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" />,
    folder: <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />,
    grip: <><circle cx="9" cy="6" r="1" /><circle cx="9" cy="12" r="1" /><circle cx="9" cy="18" r="1" /><circle cx="15" cy="6" r="1" /><circle cx="15" cy="12" r="1" /><circle cx="15" cy="18" r="1" /></>,
    split: <path d="M4 4h16v16H4zM12 4v16" />,
    // git-branch (Feather / Lucide) — канал обработки как точка ветвления
    // маршрута. Пути совпадают с утверждённым baseline DG-02, кадры A и S.
    // Tabler ti-route.
    route: <><path d="M3 19a2 2 0 1 0 4 0a2 2 0 0 0 -4 0" /><path d="M19 7a2 2 0 1 0 0 -4a2 2 0 0 0 0 4" /><path d="M11 19h5.5a3.5 3.5 0 0 0 0 -7h-8a3.5 3.5 0 0 1 0 -7h4.5" /></>,
    gitBranch: <><line x1="6" y1="3" x2="6" y2="15" /><circle cx="18" cy="6" r="3" /><circle cx="6" cy="18" r="3" /><path d="M18 9a9 9 0 0 1-9 9" /></>,
    expand: <><path d="M16 3h5v5" /><path d="M8 3H3v5" /><path d="M21 3l-7 7" /><path d="M3 3l7 7" /><path d="M16 21h5v-5" /><path d="M8 21H3v-5" /><path d="M21 21l-7-7" /><path d="M3 21l7-7" /></>,
    edit: <path d="M12 20h9M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4z" />,
    trash: <path d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2M6 7l1 13a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-13" />,
    wrench: <><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76Z" /></>,
    // Треугольник «внимание» из таблицы ICON макетов «Профиль» и «Агенты»
    // (в макете «Чат сотрудника» тот же смысл нарисован иначе — см. warning).
    alert: <path d="M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />,
    // Крестик «убрать» — таблица ICON макетов.
    close: <path d="M18 6 6 18M6 6l12 12" />,
    xCircle: <><circle cx="12" cy="12" r="9" /><line x1="9" y1="9" x2="15" y2="15" /><line x1="15" y1="9" x2="9" y2="15" /></>,
    chevron: <polyline points="6 9 12 15 18 9" />,
    chevronLeft: <polyline points="15 6 9 12 15 18" />,
    chevronRight: <polyline points="9 6 15 12 9 18" />,
    plus: <><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></>,
    arrow: <><line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" /></>,
    paperclip: <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48" />,
    send: <><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></>,
    phone: <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92Z" />,
    // Tabler ti-video: видеокамера — видеозвонок.
    video: <><path d="M15 10l4.553-2.276A1 1 0 0 1 21 8.618v6.764a1 1 0 0 1-1.447.894L15 14" /><path d="M3 6a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /></>,
    refresh: <><path d="M21 12a9 9 0 1 1-2.6-6.4L21 8" /><path d="M21 3v5h-5" /></>,
    transfer: <><path d="M17 1l4 4-4 4" /><path d="M3 11V9a4 4 0 0 1 4-4h14" /><path d="M7 23l-4-4 4-4" /><path d="M21 13v2a4 4 0 0 1-4 4H3" /></>,
    warning: <><path d="m21.7 18-8-14a2 2 0 0 0-3.5 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3Z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></>,
    bolt: <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />,
    shop: <><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z" /><path d="M3 6h18" /><path d="M16 10a4 4 0 0 1-8 0" /></>,
    search: <><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></>,
    more: <><circle cx="12" cy="5" r="1" /><circle cx="12" cy="12" r="1" /><circle cx="12" cy="19" r="1" /></>,
    external: <path d="M7 17 17 7M8 7h9v9" />,
    key: <><circle cx="7.5" cy="14.5" r="4.5" /><path d="m11 11 9-9" /><path d="m16 7 2 2" /><path d="m14 9 2 2" /></>,
    pause: <path d="M10 4H6v16h4zM18 4h-4v16h4z" />,
    play: <polygon points="7 4 20 12 7 20" fill="currentColor" stroke="none" />,
    percent: <><line x1="19" y1="5" x2="5" y2="19" /><circle cx="6.5" cy="6.5" r="2.5" /><circle cx="17.5" cy="17.5" r="2.5" /></>,
    save: <><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2Z" /><polyline points="17 21 17 13 7 13 7 21" /><polyline points="7 3 7 8 15 8" /></>,
    check: <path d="M20 6 9 17l-5-5" />,
    copy: <path d="M11 9h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-8a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2zM5 15V5a2 2 0 0 1 2-2h8" />,
    clock: <><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></>,
    reply: <><polyline points="9 17 4 12 9 7" /><path d="M20 18v-2a4 4 0 0 0-4-4H4" /></>,
    mic: <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3ZM19 10v2a7 7 0 0 1-14 0v-2M12 19v3" />,
    // Знак AI-провайдера, цилиндр хранилища и «солнце» демо-данных —
    // пути из макета «Настройки Baseline» (дизайн-базлайн v2, субменю N1–N7).
    sparkles: <><path d="M12 3l1.8 4.6L18.4 9.4 13.8 11.2 12 15.8 10.2 11.2 5.6 9.4 10.2 7.6z" /><path d="M19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z" /><path d="M5 14l.6 1.6L7.2 16.2 5.6 16.8 5 18.4l-.6-1.6L2.8 16.2l1.6-.6z" /></>,
    database: <><path d="M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3z" /><path d="M4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6" /><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3" /></>,
    sun: <path d="M12 2v4M12 18v4M4.9 4.9l2.8 2.8M16.3 16.3l2.8 2.8M2 12h4M18 12h4M4.9 19.1l2.8-2.8M16.3 7.7l2.8-2.8" />,
    // Тема и устройства сессии — пути из макета «Профиль Baseline» (кадр P1).
    sunny: <path d="M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10zM12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4" />,
    moon: <path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z" />,
    monitor: <path d="M2 4h20v12H2zM8 20h8M12 16v4" />,
    laptop: <path d="M4 5h16v11H4zM2 19h20" />,
    // Стрелка сортировки в шапке таблицы контактов (кадр K1).
    arrowDown: <path d="M12 5v14M19 12l-7 7-7-7" />,
    smartphone: <path d="M7 2h10a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2zM12 18h.01" />,
    text: <><path d="M5 5h14" /><path d="M12 5v14" /><path d="M8 19h8" /></>,
    pin: <><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" /><circle cx="12" cy="10" r="3" /></>,
    smile: <><circle cx="12" cy="12" r="10" /><path d="M8 14s1.5 2 4 2 4-2 4-2" /><line x1="9" y1="9" x2="9.01" y2="9" /><line x1="15" y1="9" x2="15.01" y2="9" /></>,
    sort: <><path d="M11 5h10" /><path d="M11 9h7" /><path d="M11 13h4" /><path d="M3 17l3 3 3-3" /><path d="M6 18V4" /></>,
    collapseLeft: <><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M9 4v16" /><path d="m15 10-2 2 2 2" /></>,
    lock: <><rect x="4" y="10" width="16" height="10" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3" /></>,
    mail: <path d="M3 7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2zM3 7l9 6 9-6" />,
    eye: <path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7zM15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0z" />,
    eyeOff: <><path d="m3 3 18 18" /><path d="M10.6 10.6a3 3 0 0 0 3.8 3.8" /><path d="M9.9 4.3A10.6 10.6 0 0 1 12 4c6.5 0 10 8 10 8a18 18 0 0 1-3.1 4.2" /><path d="M6.1 6.1C3.5 7.9 2 12 2 12s3.5 8 10 8c1.4 0 2.7-.3 3.9-.9" /></>,
    logout: <><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" /></>,
    user: <><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></>,
    link: <path d="M10 13a5 5 0 0 0 7 0l2-2a5 5 0 0 0-7-7l-1 1M14 11a5 5 0 0 0-7 0l-2 2a5 5 0 0 0 7 7l1-1" />,
    paint: <path d="M12 3a9 9 0 1 0 0 18h1a2 2 0 0 0 2-2 2 2 0 0 1 2-2h1a3 3 0 0 0 3-3 9 9 0 0 0-9-9zM8 9h.01M12 7h.01M16 9h.01" />,
    widget: <path d="M4 5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-7l-5 4z" />,
    danger: <path d="M12 3 2 20h20zM12 9v5M12 17.5v.01" />,
    image: <path d="M3 6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2zM8.5 10a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0zM4 17l5-5 4 4 3-3 4 4" />,
    file: <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8zM14 3v5h5" />,
    bold: <path d="M7 5h6a3.5 3.5 0 0 1 0 7H7zM7 12h7a3.5 3.5 0 0 1 0 7H7z" />,
    italic: <path d="M15 5h-5M14 19H9M14.5 5 10 19" />,
    code: <path d="m9 18-6-6 6-6M15 6l6 6-6 6" />,
    numlist: <path d="M10 6h11M10 12h11M10 18h11M4 5h1v4M4 15h2v1H4v2h2" />,
    quote: <path d="M7 7H4v5h3l-1 5M17 7h-3v5h3l-1 5" />,
    table: <path d="M3 5h18v14H3zM3 10h18M9 10v9" />,
    attach: <path d="M21 12.5 12.5 21a4.95 4.95 0 0 1-7-7l8-8a3.5 3.5 0 0 1 5 5l-8 8a1.95 1.95 0 0 1-3-3l7-7" />,
    undo: <path d="M9 14 4 9l5-5M4 9h11a5 5 0 0 1 0 10h-3" />,
    upload: <path d="M12 16V4M7 9l5-5 5 5M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />,
    import: <path d="M12 3v12M7 10l5 5 5-5M4 20h16" />,
    // Знание и раздел «База знаний» — раскрытая книга (ICON.doc макета «База знаний»).
    book: <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20M4 19.5A2.5 2.5 0 0 0 6.5 22H20V2H6.5A2.5 2.5 0 0 0 4 4.5z" />,
    move: <path d="M5 9l-3 3 3 3M9 5l3-3 3 3M15 19l-3 3-3-3M19 9l3 3-3 3M2 12h20M12 2v20" />,
  };
  return <svg viewBox="0 0 24 24" {...common}>{paths[name]}</svg>;
}

