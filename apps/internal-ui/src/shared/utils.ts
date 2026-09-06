export function initials(name: string, email: string): string {
  const source = name.trim() || email.split("@")[0] || "CB";
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  return source.slice(0, 2).toUpperCase();
}

const PRODUCT_COLORS = ["#0958d9", "#722ed1", "#0f9b8e", "#d4860b", "#c4456b", "#52a838", "#4c6ef0", "#eb6f4b"];

// Цвет продукта — детерминированно по коду; никаких зашитых продуктов.
export function productAccent(code: string): { bg: string; color: string } {
  let hash = 0;
  for (let index = 0; index < code.length; index += 1) hash = (hash * 31 + code.charCodeAt(index)) >>> 0;
  const color = PRODUCT_COLORS[hash % PRODUCT_COLORS.length];
  return { bg: `color-mix(in srgb, ${color} 12%, var(--surface-card))`, color };
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "long", year: "numeric" }).format(new Date(value));
}

/** Склонение по числу: pluralRu(3, ["портал", "портала", "порталов"]) → «3 портала». */
export function pluralRu(count: number, forms: [string, string, string]): string {
  const n = Math.abs(count) % 100;
  const n1 = n % 10;
  const form = n > 10 && n < 20 ? forms[2] : n1 > 1 && n1 < 5 ? forms[1] : n1 === 1 ? forms[0] : forms[2];
  return `${count} ${form}`;
}
