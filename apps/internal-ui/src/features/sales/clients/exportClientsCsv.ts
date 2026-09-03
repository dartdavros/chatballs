import type { SalesClientRowVm } from "./model";

const HEADERS = [
  "Контакт",
  "Телефон",
  "Email",
  "Логин",
  "Каналы",
  "Продукты",
  "Последний диалог",
  "Открытые диалоги",
];

function csvCell(value: string | number): string {
  const text = String(value);
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

export function exportClientsCsv(rows: SalesClientRowVm[]): void {
  const data = rows.map((client) => [
    client.name,
    client.phone,
    client.email,
    client.username,
    client.channels.map((channel) => channel.full).join(", "),
    client.products.map((product) => product.name).join(", "),
    client.lastLabel,
    client.openDialogs,
  ]);
  const csv = [HEADERS, ...data]
    .map((row) => row.map(csvCell).join(","))
    .join("\r\n");
  const url = URL.createObjectURL(
    new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = `contacts-${new Date().toISOString().slice(0, 10)}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}
