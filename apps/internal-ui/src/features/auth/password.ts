import { t } from "../../i18n";

// Функция, а не константа: в мастере первого запуска язык меняют прямо на
// экране, и застывший при импорте массив остался бы на прежнем языке.
export function passwordLabel(score: number): string {
  return [t("admin.enter_new_password"), t("admin.weak_password"), t("admin.fair_password"), t("admin.good_password"), t("admin.strong_password")][score] ?? "";
}

export function passwordScore(password: string): number {
  if (!password) return 0;
  let score = password.length >= 10 ? 1 : 0;
  if (/\d/.test(password)) score += 1;
  if (/[A-Za-zА-Яа-я]/.test(password)) score += 1;
  if (/[^A-Za-zА-Яа-я0-9]/.test(password)) score += 1;
  return Math.min(score, 4);
}

export function passwordIsValid(password: string, mismatch: boolean): boolean {
  return password.length >= 10 && /\d/.test(password) && /[A-Za-zА-Яа-я]/.test(password) && /[^A-Za-zА-Яа-я0-9]/.test(password) && !mismatch;
}
