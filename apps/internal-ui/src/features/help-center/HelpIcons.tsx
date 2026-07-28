type IconProps = { size?: number };

const iconProps = (size: number) => ({
  width: size,
  height: size,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
});

export function HelpSearchIcon({ size = 21 }: IconProps) {
  return <svg {...iconProps(size)}><circle cx="11" cy="11" r="7.5" /><path d="m20 20-3.7-3.7" /></svg>;
}

export function HelpFolderIcon({ size = 30 }: IconProps) {
  return <svg {...iconProps(size)}><path d="M3 19V6.8A1.8 1.8 0 0 1 4.8 5H9l2 2.4h8.2A1.8 1.8 0 0 1 21 9.2V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z" /></svg>;
}

export function HelpArrowIcon({ size = 18 }: IconProps) {
  return <svg {...iconProps(size)}><path d="M5 12h14M14 7l5 5-5 5" /></svg>;
}

export function HelpChevronIcon({ size = 15 }: IconProps) {
  return <svg {...iconProps(size)}><path d="m9 18 6-6-6-6" /></svg>;
}

export function HelpMessageIcon({ size = 23 }: IconProps) {
  return <svg {...iconProps(size)}><path d="M20 15a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 2-2h13a2 2 0 0 1 2 2Z" /></svg>;
}

export function HelpThumbIcon({
  direction,
  size = 21,
}: IconProps & { direction: "up" | "down" }) {
  return (
    <svg
      {...iconProps(size)}
      style={direction === "down" ? { transform: "rotate(180deg)" } : undefined}
    >
      <path d="M7 10v11H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3Z" />
      <path d="M7 10 11 3a2.2 2.2 0 0 1 4 1.8L14.5 8H20a2 2 0 0 1 2 2.4l-1.4 7A4 4 0 0 1 16.7 21H7" />
    </svg>
  );
}
