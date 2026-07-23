export function formatRussianCount(
  value: number,
  one: string,
  few: string,
  many: string,
): string {
  const tens = value % 100;
  const units = value % 10;
  const form = tens >= 11 && tens <= 14
    ? many
    : units === 1
      ? one
      : units >= 2 && units <= 4
        ? few
        : many;
  return `${value} ${form}`;
}
