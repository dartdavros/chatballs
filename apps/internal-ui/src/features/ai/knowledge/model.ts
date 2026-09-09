import { readableSize } from "../../../shared/utils";
import { t } from "../../../i18n";

export * from "./api";
export type * from "./types";

export function formatSize(bytes: number): string {
  // Байты показываются только у совсем маленьких вложений: ниже килобайта
  // «1 КБ» врало бы заметнее, чем помогало.
  return bytes < 1024 ? t("unit.b", { value: bytes }) : readableSize(bytes);
}
