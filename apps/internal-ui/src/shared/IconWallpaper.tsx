import { useEffect, useRef } from "react";
import {
  AtSign, Bot, Boxes, BriefcaseBusiness, Calendar, ChartNoAxesCombined, Cloud, Code2, Coffee, Database,
  Headset, HeartHandshake, Inbox, MailOpen, MessageCircle, MessagesSquare, Monitor, PhoneCall, Rss, Send,
  Server, Sparkles, Terminal, User, Video, createElement, type IconNode,
} from "lucide";

// Фоновый узор из lucide-иконок (макет владельца «Chatbolls — Lucide Pattern»):
// филлотаксис по золотому углу с тремя вихрями, размер/прозрачность/поворот —
// квазислучайные ряды. Алгоритм и константы повторяют макет один в один; цвета
// фона и штриха — токены --wallpaper-bg / --wallpaper-ink (две темы).
// Строится императивно (≈900 svg) и перестраивается по размеру контейнера.

const ICONS: IconNode[] = [
  AtSign, Bot, Boxes, BriefcaseBusiness, Calendar, ChartNoAxesCombined, Cloud, Code2, Coffee, Database,
  Headset, HeartHandshake, Inbox, MailOpen, MessageCircle, MessagesSquare, Monitor, PhoneCall, Rss, Send,
  Server, Sparkles, Terminal, User, Video,
];

const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));

function fract(x: number): number {
  return x - Math.floor(x);
}

function quasi(index: number, channel = 0): number {
  const a = 0.7548776662466927;
  const b = 0.5698402909980532;
  return fract((index + 1) * a + channel * b);
}

function iconFor(i: number, ring: number): IconNode {
  return ICONS[(i * 11 + ring * 7 + Math.floor(i / 9) * 3) % ICONS.length];
}

function build(pattern: HTMLElement, width: number, height: number): void {
  pattern.replaceChildren();
  const w = width + 240;
  const h = height + 240;
  const cx = w / 2;
  const cy = h / 2;
  const maxR = Math.hypot(w / 2, h / 2) + 90;
  const radialStep = w < 900 ? 34 : 38;
  const total = Math.ceil((maxR / radialStep) ** 2) + 40;
  const vortices = [
    { x: w * 0.22, y: h * 0.28, strength: 34, sigma: Math.min(w, h) * 0.28, sign: 1 },
    { x: w * 0.74, y: h * 0.34, strength: 29, sigma: Math.min(w, h) * 0.26, sign: -1 },
    { x: w * 0.55, y: h * 0.78, strength: 31, sigma: Math.min(w, h) * 0.3, sign: 1 },
  ];
  const fragment = document.createDocumentFragment();
  for (let i = 0; i < total; i += 1) {
    const r = radialStep * Math.sqrt(i);
    const theta = i * GOLDEN_ANGLE;
    let x = cx + r * Math.cos(theta);
    let y = cy + r * Math.sin(theta);
    let vx = 0;
    let vy = 0;
    for (const vortex of vortices) {
      const dx = x - vortex.x;
      const dy = y - vortex.y;
      const d2 = dx * dx + dy * dy;
      const sigma2 = vortex.sigma * vortex.sigma;
      const influence = Math.exp(-d2 / (2 * sigma2));
      const len = Math.max(1, Math.sqrt(d2));
      vx += (-dy / len) * vortex.strength * influence * vortex.sign;
      vy += (dx / len) * vortex.strength * influence * vortex.sign;
    }
    x += vx;
    y += vy;
    if (x < -40 || x > w + 40 || y < -40 || y > h + 40) continue;
    const snow = 0.5 + 0.5 * Math.cos(6 * theta + r * 0.015);
    const wave = 0.5 + 0.5 * Math.sin(i * 0.71 + r * 0.024);
    const size = 15 + 16 * (0.42 * snow + 0.58 * wave);
    const opacity = 0.085 + 0.105 * (0.35 * snow + 0.65 * quasi(i, 2));
    const flowAngle = (Math.atan2(vy, vx || 0.0001) * 180) / Math.PI;
    const rotation = (Math.abs(vx) + Math.abs(vy) > 1 ? flowAngle : (theta * 180) / Math.PI) + (quasi(i, 3) - 0.5) * 14;

    const glyph = document.createElement("span");
    glyph.className = "wallpaper-glyph";
    glyph.style.left = `${x}px`;
    glyph.style.top = `${y}px`;
    glyph.style.width = `${size}px`;
    glyph.style.height = `${size}px`;
    glyph.style.opacity = opacity.toFixed(3);
    glyph.style.transform = `translate(-50%, -50%) rotate(${rotation.toFixed(2)}deg)`;
    glyph.appendChild(createElement(iconFor(i, Math.floor(r / radialStep)), { "stroke-width": 1.45 }));
    fragment.appendChild(glyph);
  }
  pattern.appendChild(fragment);
}

export function IconWallpaper({ className = "" }: { className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const host = ref.current;
    const pattern = host?.firstElementChild as HTMLElement | null;
    if (!host || !pattern || typeof ResizeObserver === "undefined") return;
    let timer: number | undefined;
    const rebuild = () => {
      const rect = host.getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0) build(pattern, rect.width, rect.height);
    };
    const observer = new ResizeObserver(() => {
      window.clearTimeout(timer);
      timer = window.setTimeout(rebuild, 120);
    });
    observer.observe(host);
    rebuild();
    return () => {
      observer.disconnect();
      window.clearTimeout(timer);
    };
  }, []);
  return (
    <div className={`icon-wallpaper ${className}`} ref={ref} aria-hidden="true">
      <div className="wallpaper-pattern" />
    </div>
  );
}
