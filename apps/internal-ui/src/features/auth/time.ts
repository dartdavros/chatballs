export function formatCountdown(seconds: number): string {
  return `0:${seconds.toString().padStart(2, "0")}`;
}
