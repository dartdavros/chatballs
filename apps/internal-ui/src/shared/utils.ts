export function initials(name: string, email: string): string {
  const source = name.trim() || email.split("@")[0] || "EH";
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  return source.slice(0, 2).toUpperCase();
}

export function productAccent(code: string): { bg: string; color: string } {
  if (code === "foxray") return { bg: "#f9f0ff", color: "#722ed1" };
  return { bg: "#e6f4ff", color: "#0958d9" };
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "long", year: "numeric" }).format(new Date(value));
}
